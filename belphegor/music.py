import discord
from discord.ext import commands
import asyncio
import pafy
from . import utils
from .utils import config, token
from apiclient.discovery import build
from discord.opus import Encoder as OpusEncoder
import queue
from threading import Thread
from io import BytesIO
import json
import locale
import random
import re
from pymongo import ReturnDocument

#==================================================================================================================================================

class Buffer(queue.Queue):
    def get(self):
        with self.not_empty:
            if not self.queue:
                self.not_empty.wait()
            item = self.queue.popleft()
            self.not_full.notify()
            return item

    def _discard(self, number):
        with self.mutex:
            item = None
            for i in range(min(number, len(self.queue))):
                item = self.queue.popleft()
                if item[0] == b"":
                    self.queue.append((b"", item[1]))
                    break
            self.not_full.notify()
            return item[1]

#==================================================================================================================================================

class FFmpegWithBuffer(discord.FFmpegPCMAudio):
    def __init__(self, *args, **kwargs):
        discord.FFmpegPCMAudio.__init__(self, *args, **kwargs)
        self._buffer = Buffer(config.BUFFER_SIZE)
        self.counter = 0
        thread = Thread(target=self.read_buffer, args=())
        thread.daemon = True
        thread.start()

    def read(self):
        item = self._buffer.get()
        self.counter = item[1]
        return item[0]

    def read_buffer(self):
        counter = 0
        while True:
            ret = self._stdout.read(OpusEncoder.FRAME_SIZE)
            counter += 1
            if len(ret) != OpusEncoder.FRAME_SIZE:
                self._buffer.put((b"", counter))
                return
            self._buffer.put((ret, counter))

    def fast_forward(self, number):
        return self._buffer._discard(number)

#==================================================================================================================================================

class Song:
    def __init__(self, requestor, title, url):
        self.requestor = requestor
        self.title = utils.discord_escape(title)
        self.url = url
        self.default_volume = 1.0

    def raw_update(self):
        video = pafy.new(self.url)
        audio = video.getbestaudio()
        for a in video.audiostreams:
            if a.bitrate == "128k":
                audio = a
                break
        try:
            url = audio.url
        except:
            url = video.streams[-1].url
        self.duration = video.duration
        self.music = discord.PCMVolumeTransformer(
            FFmpegWithBuffer(
                url,
                before_options="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 2"
            ),
            volume=self.default_volume
        )

    def info(self):
        second_elapsed = int(self.music.original.counter * 0.02)
        return f"{self.title} ({second_elapsed//3600:02}:{second_elapsed%3600//60:02}:{second_elapsed%60:02} / {self.duration})"

    def time_elapsed(self):
        second_elapsed = int(self.music.original.counter * 0.02)
        return (second_elapsed//3600, second_elapsed%3600//60, second_elapsed%60)

    def to_dict(self):
        if self.requestor:
            id = self.requestor.id
        else:
            id = None
        return {"requestor_id": id, "title": self.title, "url": self.url}

#==================================================================================================================================================

class Playlist():
    def __init__(self, bot, guild_id):
        self.playlist_data = bot.db.music_playlist_data
        self.guild_id = guild_id
        self.playlist = []
        self._wait = asyncio.Event()
        self._lock = asyncio.Lock()

    async def put(self, song):
        async with self._lock:
            self.playlist.append(song)
            self._wait.set()
            await self.playlist_data.update_one({"guild_id": self.guild_id}, {"$push": {"playlist": song.to_dict()}})

    async def put_many(self, songs):
        if songs:
            async with self._lock:
                self.playlist.extend(songs)
                self._wait.set()
                await self.playlist_data.update_one({"guild_id": self.guild_id}, {"$push": {"playlist": {"$each": [s.to_dict() for s in songs]}}})

    async def get(self):
        if not self.playlist:
            self._wait.clear()
            await self._wait.wait()
        async with self._lock:
            song = self.playlist.pop(0)
            await self.playlist_data.update_one({"guild_id": self.guild_id}, {"$pop": {"playlist": -1}})
            return song

    async def delete(self, position):
        async with self._lock:
            self.playlist.pop(position)
            await self.playlist_data.update_one({"guild_id": self.guild_id}, {"$set": {"playlist": [s.to_dict() for s in self.playlist]}})

    async def purge(self):
        async with self._lock:
            self.playlist.clear()
            await self.playlist_data.update_one({"guild_id": self.guild_id}, {"$set": {"playlist": []}})

    def size(self):
        return len(self.playlist)

    def display_playlist(self):
        playlist = []
        for index, song in enumerate(self.playlist):
            playlist.append(f"{index+1}. [{song.title}]({song.url})")
        return playlist

    def __call__(self, position):
        try:
            return self.playlist[position]
        except:
            return None

#==================================================================================================================================================

class MusicPlayer:
    def __init__(self, bot, guild_id, *, initial=[]):
        self.bot = bot
        self.guild_id = guild_id
        self.queue = Playlist(bot, guild_id)
        self.voice_client = None
        self.current_song = None
        self.play_next_song = asyncio.Event()
        self.repeat = False
        self.channel = None
        self.player = None
        self.lock = asyncio.Lock()
        guild = bot.get_guild(guild_id)
        self.queue.playlist.extend([Song(guild.get_member(s["requestor_id"]), s["title"], s["url"]) for s in initial])

    def ready_to_play(self, voice_client):
        self.voice_client = voice_client
        self.player = self.bot.loop.create_task(self.play_till_eternity())

    def skip(self):
        if self.voice_client.is_playing():
            self.voice_client.stop()
            self.current_song = None

    def _next_part(self, e=None):
        if e:
            print(e)
        if not self.repeat:
            self.current_song = None
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def leave_voice(self):
        self.player.cancel()
        self.player = None
        self.repeat = False
        await self.voice_client.disconnect(force=True)
        self.voice_client = None

    async def play_till_eternity(self):
        try:
            while True:
                self.play_next_song.clear()
                if not self.current_song:
                    try:
                        self.current_song = await asyncio.wait_for(self.queue.get(), 120, loop=self.bot.loop)
                    except asyncio.TimeoutError:
                        try:
                            self.bot.loop.create_task(self.leave_voice())
                            self.bot.loop.create_task(self.channel.send("*\"No music? Time to sleep then. Yaaawwnnnn~~\"*"))
                            return
                        except:
                            return
                await self.bot.loop.run_in_executor(None, self.current_song.raw_update)
                self.voice_client.play(self.current_song.music, after=self._next_part)
                name = utils.discord_escape(self.current_song.requestor.display_name)
                await self.channel.send(f"Playing **{self.current_song.title}** requested by {name}.")
                await self.play_next_song.wait()
        except asyncio.CancelledError:
            return

#==================================================================================================================================================

class MusicBot:
    '''
    Music is life.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.playlist_data = bot.db.music_playlist_data
        self.music_players = {}
        locale.setlocale(locale.LC_ALL, '')
        self.youtube = build("youtube", "v3", developerKey=token.GOOGLE_CLIENT_API_KEY)
        self.lock = asyncio.Lock()

    async def get_music_player(self, guild_id):
        mp = self.music_players.get(guild_id)
        if not mp:
            mp_data = await self.playlist_data.find_one_and_update(
                {"guild_id": guild_id},
                {"$setOnInsert": {"guild_id": guild_id, "playlist": []}},
                return_document=ReturnDocument.AFTER,
                upsert=True
            )
            mp = MusicPlayer(self.bot, guild_id, initial=mp_data["playlist"])
            self.music_players[guild_id] = mp
        return mp

    @commands.group(aliases=["m",])
    async def music(self, ctx):
        if ctx.invoked_subcommand is None:
            message = ctx.message
            message.content = ">>help music"
            await self.bot.process_commands(message)

    @music.command(aliases=["j",])
    async def join(self, ctx):
        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            return await ctx.send("You are not in a voice channel.")
        music_player = await self.get_music_player(voice_channel.guild.id)
        async with music_player.lock:
            msg = await ctx.send("Connecting...")
            current_voice = discord.utils.find(lambda vc: vc.guild.id==voice_channel.guild.id, self.bot.voice_clients)
            if current_voice:
                await current_voice.disconnect(force=True)
            try:
                voice_client = await voice_channel.connect(timeout=20, reconnect=True)
            except:
                return await msg.edit(content="Cannot connect to voice. Try joining other voice channel.")
            music_player.ready_to_play(voice_client)
            music_player.channel = ctx.channel
            await msg.edit(content=f"{self.bot.user.display_name} joined {voice_channel.name}.")

    @music.command(aliases=["l",])
    async def leave(self, ctx):
        music_player = await self.get_music_player(ctx.guild.id)
        await music_player.lock.acquire()
        try:
            name = music_player.voice_client.channel.name
            await music_player.leave_voice()
            await ctx.send(f"{self.bot.user.display_name} left {name}.")
        except AttributeError:
            await ctx.send(f"{self.bot.user.display_name} is not in any voice channel.")
        music_player.lock.release()

    def youtube_search(self, name, type="video"):
        search_response = self.youtube.search().list(q=name, part="id,snippet", type=type, maxResults=10).execute()
        results = []
        for search_result in search_response.get("items", None):
            results.append(search_result)
            if len(results) > 4:
                break
        return results

    @music.command(aliases=["q",])
    async def queue(self, ctx, *, name:str=""):
        music_player = await self.get_music_player(ctx.guild.id)
        if not name:
            try:
                if music_player.voice_client.is_playing():
                    state = "Playing"
                else:
                    state = "Paused"
            except:
                state = "Stopped"
            playlist = music_player.queue.display_playlist()
            try:
                current_song_info = music_player.current_song.info()
            except:
                current_song_info = ""
            if playlist:
                page_data = []
                for i,p in enumerate(playlist):
                    if i%10==0:
                        page_data.append(p)
                    else:
                        page_data[i//10] = f"{page_data[i//10]}\n\n{p}"
                current_page = 0
                max_page = len(page_data)
                embed = discord.Embed(title=f"({state}) {current_song_info}", colour=discord.Colour.green())
                embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
                embed.set_footer(text=f"(Page {1}/{max_page})")

                def data(page):
                    embed.description = page_data[page]
                    embed.set_footer(text=f"(Page {page+1}/{max_page})")
                    return embed

                await ctx.embed_page(max_page=max_page, embed=data)
            else:
                await ctx.send(embed=discord.Embed(title=f"({state}) {current_song_info}", colour=discord.Colour.green()))
        else:
            async with self.lock:
                results = await self.bot.loop.run_in_executor(None, self.youtube_search, name)
            stuff = '\n\n'.join([f"{i+1}: [{utils.discord_escape(v['snippet']['title'])}](https://youtu.be/{v['id']['videoId']})" for i,v in enumerate(results)])
            embed = discord.Embed(title="\U0001f3b5 Video search result: ", description=f"{stuff}\n\n<>: cancel", colour=discord.Colour.green())
            embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
            await ctx.send(embed=embed)
            message = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.author.id)
            try:
                choose = int(message.content) - 1
                if choose in range(5):
                    result = results[choose]
                else:
                    return
            except Exception as e:
                #print(e)
                return
            title = result["snippet"]["title"]
            await music_player.queue.put(Song(ctx.message.author, title, f"https://youtu.be/{result['id']['videoId']}"))
            await ctx.send(f"Added **{title}** to queue.")

    @music.command(aliases=["s",])
    async def skip(self, ctx):
        music_player = await self.get_music_player(ctx.guild.id)
        music_player.skip()

    @music.command(aliases=["v",])
    async def volume(self, ctx, vol:int):
        music_player = await self.get_music_player(ctx.guild.id)
        if 0 <= vol <= 200:
            music_player.current_song.default_volume = vol / 100
            music_player.current_song.music.volume = vol / 100
            await ctx.send(f"Volume for current song has been set to {vol}%.")
        else:
            await ctx.send("Volume must be between 0 and 200.")

    @music.command(aliases=["r",])
    async def repeat(self, ctx):
        music_player = await self.get_music_player(ctx.guild.id)
        if music_player.repeat:
            music_player.repeat = False
            await ctx.send("Repeat mode has been turned off.")
        else:
            music_player.repeat = True
            await ctx.send("Repeat mode has been turned on.")

    @music.command(aliases=["d",])
    async def delete(self, ctx, position:int):
        music_player = await self.get_music_player(ctx.guild.id)
        if 0 < position <= music_player.queue.size():
            title = music_player.queue[position].title
            sentences = {
                "initial":  "Delet this?",
                "yes":      f"Deleted **{title}** from queue.",
                "no":       "Cancelled deleting.",
                "timeout":  "Timeout, cancelled deleting."
            }
            check = await ctx.yes_no_prompt(sentences=sentences)
            if check:
                await music_player.queue.delete(position-1)
        else:
            await ctx.send("Position out of range.")

    @music.command()
    async def purge(self, ctx):
        music_player = await self.get_music_player(ctx.guild.id)
        sentences = {
            "initial":  f"Purge queue?",
            "yes":      "Queue purged.",
            "no":       "Cancelled purging.",
            "timeout":  "Timeout, cancelled purging."
        }
        check = await ctx.yes_no_prompt(sentences=sentences)
        if check:
            await music_player.queue.purge()

    @music.command()
    async def export(self, ctx, *, name="playlist"):
        music_player = await self.get_music_player(ctx.guild.id)
        jsonable = []
        if music_player.current_song:
            jsonable.append({"title": music_player.current_song.title, "url": music_player.current_song.url})
        for song in music_player.queue.playlist:
            jsonable.append({"title": song.title, "url": song.url})
        bytes_ = json.dumps(jsonable, indent=4, ensure_ascii=False).encode("utf-8")
        await ctx.send(file=discord.File(bytes_, f"{name}.json"))

    @music.command(name="import")
    async def music_import(self, ctx):
        music_player = await self.get_music_player(ctx.guild.id)
        msg = ctx.message
        if not ctx.message.attachments:
            await msg.add_reaction("\U0001f504")
            try:
                msg = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.author.id and m.attachments, timeout=120)
            except asyncio.TimeoutError:
                try:
                    return await msg.clear_reactions()
                except:
                    return
            try:
                await ctx.message.clear_reactions()
            except:
                return
        bytes_ = BytesIO()
        await msg.attachments[0].save(bytes_)
        playlist = json.loads(bytes_.getvalue().decode("utf-8"))
        try:
            await music_player.queue.put_many([Song(msg.author, s["title"], s["url"]) for s in playlist])
            await ctx.send(f"Added {len(playlist)} songs to queue.")
        except:
            await ctx.send("Wrong format for imported file.")

    def youtube_playlist_items(self, message, playlist_id):
        results = []
        playlist_items = self.youtube.playlistItems().list(playlistId=playlist_id, part="snippet", maxResults=50).execute()
        for song in playlist_items.get("items", None):
            if song["snippet"]["title"] in ("Deleted video", "Private video"):
                continue
            else:
                results.append(Song(message.author, song["snippet"]["title"], f"https://youtu.be/{song['snippet']['resourceId']['videoId']}"))
        while playlist_items.get("nextPageToken", None):
            playlist_items = self.youtube.playlistItems().list(playlistId=playlist_id, part="snippet", maxResults=50, pageToken=playlist_items["nextPageToken"]).execute()
            for song in playlist_items.get("items", None):
                if song["snippet"]["title"] in ("Deleted video", "Private video"):
                    continue
                else:
                    results.append(Song(message.author, song["snippet"]["title"], f"https://youtu.be/{song['snippet']['resourceId']['videoId']}"))
        return results

    @music.command(aliases=["p",])
    async def playlist(self, ctx, *, name):
        music_player = await self.get_music_player(ctx.guild.id)
        if name.startswith("-random "):
            shuffle = True
            name = name[8:]
        elif name.startswith("-r "):
            shuffle = True
            name = name[3:]
        else:
            shuffle = False
        async with self.lock:
            results = await self.bot.loop.run_in_executor(None, self.youtube_search, name, "playlist")
        stuff = '\n\n'.join([f"{i+1}: [{utils.discord_escape(p['snippet']['title'])}](https://www.youtube.com/playlist?list={p['id']['playlistId']})\nBy: {p['snippet']['channelTitle']}" for i,p in enumerate(results)])
        embed = discord.Embed(title="\U0001f3b5 Playlist search result: ", description=f"{stuff}\n\n<>: cancel", colour=discord.Colour.green())
        embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
        await ctx.send(embed=embed)
        message = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.author.id)
        try:
            choose = int(message.content) - 1
            if choose in range(5):
                result = results[choose]
            else:
                return
        except Exception as e:
            #print(e)
            return
        async with ctx.typing():
            async with self.lock:
                items = await self.bot.loop.run_in_executor(None, self.youtube_playlist_items, ctx.message, result["id"]["playlistId"])
            if shuffle:
                random.shuffle(items)
                add_text = " in random position"
            else:
                add_text = ""
            await music_player.queue.put_many(items)
            await ctx.send(f"Added {len(items)} songs to queue{add_text}.")

    def youtube_video_info(self, url):
        video_id = url[17:]
        result = self.youtube.videos().list(part='snippet,contentDetails,statistics', id=video_id).execute()
        video = result["items"][0]
        return video

    @music.command(aliases=["i",])
    async def info(self, ctx, position: int=0):
        music_player = await self.get_music_player(ctx.guild.id)
        position -= 1
        if position < 0:
            try:
                url = music_player.current_song.url
                video = await self.bot.loop.run_in_executor(None, self.youtube_video_info, url)
            except:
                return await ctx.send("No song is currently playing.")
        elif position < music_player.queue.size():
            url = music_player.queue(position).url
            video = await self.bot.loop.run_in_executor(None, self.youtube_video_info, url)
        else:
            return await ctx.send("Position out of range.")

        snippet = video["snippet"]
        description = utils.unifix(snippet["description"]).strip()
        description_page = utils.split_page(description, 500)
        max_page = len(description_page)
        embed = discord.Embed(title=f"\U0001f3b5 {snippet['title']}", url=url, colour=discord.Colour.green())
        embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
        embed.add_field(name="Uploader", value=f"[{snippet['channelTitle']}](https://www.youtube.com/channel/{snippet['channelId']})")
        embed.add_field(name="Date", value=snippet["publishedAt"][:10])
        embed.add_field(name="Duration", value=f"\U0001f552 {video['contentDetails'].get('duration', '0s')[2:].lower()}")
        embed.add_field(name="Views", value=f"\U0001f441 {int(video['statistics'].get('viewCount', 0)):n}")
        embed.add_field(name="Likes", value=f"\U0001f44d {int(video['statistics'].get('likeCount', 0)):n}")
        embed.add_field(name="Dislikes", value=f"\U0001f44e {int(video['statistics'].get('dislikeCount', 0)):n}")
        embed.add_field(name="Description", value="desu", inline=False)
        for key in ("maxres", "standard", "high", "medium", "default"):
            value = snippet["thumbnails"].get(key, None)
            if value is not None:
                embed.set_image(url=value["url"])
                break

        def data(page):
            embed.set_field_at(6, name="Description", value=f"{description_page[page]}\n\n(Page {page+1}/{max_page})", inline=False)
            return embed

        await ctx.embed_page(max_page=max_page, embed=data)

    @music.command(aliases=["t",])
    async def toggle(self, ctx):
        music_player = await self.get_music_player(ctx.guild.id)
        vc = music_player.voice_client
        if vc.is_paused():
            vc.resume()
            await ctx.send("Resumed playing.")
        elif vc.is_playing():
            vc.pause()
            await ctx.send("Paused.")

    @music.command(aliases=["f"])
    async def forward(self, ctx, seconds: int=10):
        music_player = await self.get_music_player(ctx.guild.id)
        song = music_player.current_song
        if song:
            if 0 < seconds < 60:
                tbefore = song.time_elapsed()
                safter = int(song.music.original.fast_forward(seconds*50) * 0.02)
                tafter = (safter//3600, safter%3600//60, safter%60)
                await ctx.send(f"Forward from {tbefore[0]:02}:{tbefore[1]:02}:{tbefore[2]:02} to {tafter[0]:02}:{tafter[1]:02}:{tafter[2]:02}.")
            else:
                await ctx.send("Fast forward time must be between 1 and 59 seconds.")
        else:
            await ctx.send("No song is currently playing.")

    @music.command()
    async def setchannel(self, ctx):
        music_player = await self.get_music_player(ctx.guild.id)
        music_player.channel = ctx.channel
        await ctx.confirm()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(MusicBot(bot))