import discord
from discord.ext import commands
import asyncio
import pafy
from . import utils
from .utils import config, token, data_type, checks
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
import copy

#==================================================================================================================================================

youtube_match = re.compile(r"(?:https?\:\/\/)?(?:www\.)?(?:youtube(?:-nocookie)?\.com\/\S*[^\w\s-]|youtu\.be\/)([\w-]{11})(?:[^\w\s-]|$)")

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
        with self.not_empty:
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
        self._is_running = True
        thread = Thread(target=self.read_buffer, args=())
        thread.daemon = True
        thread.start()

    def read(self):
        item = self._buffer.get()
        self.counter = item[1]
        return item[0]

    def read_buffer(self):
        counter = 0
        while self._is_running:
            chunk = self._stdout.read(OpusEncoder.FRAME_SIZE)
            counter += 1
            if len(chunk) != OpusEncoder.FRAME_SIZE:
                self._buffer.put((b"", counter))
                return
            self._buffer.put((chunk, counter))

    def fast_forward(self, number):
        return self._buffer._discard(number)

    def cleanup(self):
        self._is_running = False
        super().cleanup()

#==================================================================================================================================================

class Song:
    __slots__ = ("requestor", "title", "url", "default_volume", "index", "duration", "music")

    def __init__(self, requestor, title, url):
        self.requestor = requestor
        self.title = utils.discord_escape(title)
        self.url = url
        self.default_volume = 1.0
        self.index = 0

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
                before_options="-hide_banner -loglevel panic -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 2"
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
        return {"requestor_id": getattr(self.requestor, "id", None), "title": self.title, "url": self.url}

#==================================================================================================================================================

class Playlist:
    def __init__(self, bot, guild_id, *, next_index):
        self.playlist_data = bot.db.music_playlist_data
        self.guild_id = guild_id
        self.playlist = []
        self._wait = asyncio.Event()
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)
        self.next_index = next_index

    async def put(self, song):
        async with self._not_full:
            song.index = self.next_index
            self.next_index += 1
            self.playlist.append(song)
            await self.playlist_data.update_one(
                {
                    "guild_id": self.guild_id
                },
                {
                    "$set": {
                        "next_index": self.next_index
                    },
                    "$push": {
                        "playlist": song.to_dict()
                    }
                }
            )
            self._not_empty.notify()

    async def put_many(self, songs):
        if songs:
            async with self._not_full:
                for s in songs:
                    s.index = self.next_index
                    self.next_index += 1
                self.playlist.extend(songs)
                await self.playlist_data.update_one(
                    {
                        "guild_id": self.guild_id
                    },
                    {
                        "$set": {
                            "next_index": self.next_index
                        },
                        "$push": {
                            "playlist": {
                                "$each": [s.to_dict() for s in songs]
                            }
                        }
                    }
                )
                self._not_empty.notify()

    async def get(self):
        async with self._not_empty:
            if not self.size():
                await self._not_empty.wait()
            song = self.playlist.pop(0)
            await self.playlist_data.update_one({"guild_id": self.guild_id}, {"$pop": {"playlist": -1}})
            return song

    async def delete(self, position):
        async with self._not_empty:
            song = self.playlist.pop(position)
            await self.playlist_data.update_one({"guild_id": self.guild_id}, {"$pull": {"playlist": {"index": song.index}}})
            return song

    async def purge(self):
        async with self._not_empty:
            self.playlist.clear()
            await self.playlist_data.update_one({"guild_id": self.guild_id}, {"$set": {"playlist": []}})

    def size(self):
        return len(self.playlist)

    def __call__(self, position):
        try:
            return self.playlist[position]
        except:
            return None

#==================================================================================================================================================

class MusicPlayer:
    def __init__(self, bot, guild_id, *, initial, next_index):
        self.bot = bot
        self.in_voice_channel = False
        self.guild_id = guild_id
        self.queue = Playlist(bot, guild_id, next_index=next_index)
        self.voice_client = None
        self.current_song = None
        self.play_next_song = asyncio.Event()
        self.repeat = False
        self.channel = None
        self.player = None
        self.lock = asyncio.Lock()
        guild = bot.get_guild(guild_id)
        self.queue.playlist.extend((Song(guild.get_member(s["requestor_id"]), s["title"], s["url"]) for s in initial))
        self.auto_info = None

    def ready_to_play(self, voice_client):
        self.in_voice_channel = True
        self.voice_client = voice_client
        self.player = self.bot.loop.create_task(self.play_till_eternity())

    def skip(self):
        if self.voice_client.is_playing():
            self.voice_client.stop()
            self.current_song = None

    async def leave_voice(self):
        self.in_voice_channel = False
        self.repeat = False
        try:
            self.player.cancel()
        except:
            pass
        try:
            await self.voice_client.disconnect(force=True)
        except:
            pass

    async def play_till_eternity(self):
        def _next_part(e=None):
            if e:
                print(e)
            if not self.repeat:
                self.current_song = None
            self.bot.loop.call_soon_threadsafe(self.play_next_song.set)
        cmd = self.bot.get_command("music info")

        while self.in_voice_channel:
            self.play_next_song.clear()
            if not self.current_song:
                try:
                    self.current_song = await asyncio.wait_for(self.queue.get(), 120, loop=self.bot.loop)
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.leave_voice())
                    self.bot.loop.create_task(self.channel.send("No music? Time to sleep then. Yaaawwnnnn~~"))
                    return
            await self.bot.loop.run_in_executor(None, self.current_song.raw_update)
            self.voice_client.play(self.current_song.music, after=_next_part)
            name = utils.discord_escape(getattr(self.current_song.requestor, "display_name", "<user left server>"))
            await self.channel.send(f"Playing **{self.current_song.title}** requested by {name}.")
            if self.auto_info:
                try:
                    new_msg = copy.copy(self.auto_info)
                    new_msg.author = self.current_song.requestor or new_msg.author
                    new_ctx = await self.bot.get_context(new_msg, cls=data_type.BelphegorContext)
                    await new_ctx.invoke(self.bot.get_command("music info"))
                except Exception as e:
                    print(e)
            await self.play_next_song.wait()

#==================================================================================================================================================

class Music:
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

    def cleanup(self):
        for mp in self.music_players.values():
            self.bot.create_task_and_count(mp.leave_voice())

    async def get_music_player(self, guild_id):
        mp = self.music_players.get(guild_id)
        if not mp:
            mp_data = await self.playlist_data.find_one_and_update(
                {"guild_id": guild_id},
                {"$setOnInsert": {"guild_id": guild_id, "next_index": 0, "playlist": []}},
                return_document=ReturnDocument.AFTER,
                upsert=True
            )
            mp = MusicPlayer(self.bot, guild_id, initial=mp_data["playlist"], next_index=mp_data["next_index"])
            self.music_players[guild_id] = mp
        return mp

    @commands.group(aliases=["m"])
    @checks.guild_only()
    async def music(self, ctx):
        '''
            `>>music`
            Base command. Does nothing by itself, but with subcommands can be used to play music.
        '''
        if ctx.invoked_subcommand is None:
            pass

    @music.command(aliases=["j"])
    async def join(self, ctx):
        '''
            `>>music join`
            Have {0} join the current voice channel you are in and play everything in queue.
            May or may not bug out when the connection is unstable. If that happens, try move her to another channel.
        '''
        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            return await ctx.send("You are not in a voice channel.")
        music_player = await self.get_music_player(voice_channel.guild.id)
        async with music_player.lock:
            msg = await ctx.send("Connecting...")
            if ctx.voice_client:
                await ctx.voice_client.disconnect(force=True)
            try:
                voice_client = await voice_channel.connect(timeout=20, reconnect=False)
            except:
                return await msg.edit(content="Cannot connect to voice. Try joining other voice channel.")
            else:
                self.bot.loop.create_task(msg.edit(content=f"{self.bot.user.display_name} joined {voice_channel.name}."))
            music_player.ready_to_play(voice_client)
            music_player.channel = ctx.channel

    @music.command(aliases=["l"])
    async def leave(self, ctx):
        '''
            `>>music leave`
            Have {0} leave voice channel.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        async with music_player.lock:
            try:
                name = music_player.voice_client.channel.name
            except AttributeError:
                await ctx.send(f"{self.bot.user.display_name} is not in any voice channel.")
            else:
                await music_player.leave_voice()
                await ctx.send(f"{self.bot.user.display_name} left {name}.")

    def youtube_search(self, name, type="video"):
        search_response = self.youtube.search().list(q=name, part="id,snippet", type=type, maxResults=10).execute()
        results = []
        for search_result in search_response.get("items", None):
            results.append(search_result)
            if len(results) > 4:
                break
        return results

    def current_queue_info(self, music_player):
        try:
            if music_player.voice_client.is_playing():
                state = "Playing"
            else:
                state = "Paused"
        except:
            state = "Stopped"
        playlist = music_player.queue.playlist
        try:
            current_song_info = music_player.current_song.info()
        except:
            current_song_info = ""
        if playlist:
            return utils.embed_page_format(
                playlist, 10, separator="\n\n",
                title=f"({state}) {current_song_info}",
                description=lambda i, x: f"`{i+1}.` **[{x.title}]({x.url})**",
                colour=discord.Colour.green(),
                thumbnail_url="http://i.imgur.com/HKIOv84.png"
                )
        else:
            return [discord.Embed(title=f"({state}) {current_song_info}", colour=discord.Colour.green())]

    @music.command(aliases=["q"])
    async def queue(self, ctx, *, name=None):
        '''
            `>>music queue <optional: name>`
            Search Youtube for a song and put it in queue.
            If no name is provided, the current queue is displayed instead.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        if not name:
            embeds = self.current_queue_info(music_player)
            return await ctx.embed_page(embeds)
        if 1 + music_player.queue.size() > 1000:
            return await ctx.send("Too many entries.")
        async with ctx.typing():
            results = await self.bot.run_in_lock(self.lock, self.youtube_search, name)
            stuff = "\n\n".join([
                f"`{i+1}:` **[{utils.discord_escape(v['snippet']['title'])}](https://youtu.be/{v['id']['videoId']})**\n      By: {v['snippet']['channelTitle']}"
                for i,v in enumerate(results)
            ])
            embed = discord.Embed(title="\U0001f3b5 Video search result: ", description=f"{stuff}\n\n`<>:` cancel", colour=discord.Colour.green())
            embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
            await ctx.send(embed=embed)
            index = await ctx.wait_for_choice(max=len(results))
            if index is None:
                return
            else:
                result = results[index]
            title = result["snippet"]["title"]
            await music_player.queue.put(Song(ctx.message.author, title, f"https://youtu.be/{result['id']['videoId']}"))
            await ctx.send(f"Added **{title}** to queue.")

    @music.command(aliases=["s"])
    async def skip(self, ctx):
        '''
            `>>music skip`
            Skip current song.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        music_player.skip()

    @music.command(aliases=["v"])
    async def volume(self, ctx, vol: int):
        '''
            `>>music volume <value>`
            Set volume. Volume must be an integer between 0 and 200.
            Default volume is 100.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        if 0 <= vol <= 200:
            if music_player.current_song:
                music_player.current_song.default_volume = vol / 100
                music_player.current_song.music.volume = vol / 100
            await ctx.send(f"Volume for current song has been set to {vol}%.")
        else:
            await ctx.send("Volume must be between 0 and 200.")

    @music.command(aliases=["r"])
    async def repeat(self, ctx):
        '''
            `>>music repeat`
            Turn on repeat mode. The current song will be repeated indefinitely.
            Use again to switch it off.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        if music_player.repeat:
            music_player.repeat = False
            await ctx.send("Repeat mode has been turned off.")
        else:
            music_player.repeat = True
            await ctx.send("Repeat mode has been turned on.")

    @music.command(aliases=["d"])
    async def delete(self, ctx, position: int):
        '''
            `>>music delete <position>`
            Delete a song from queue.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        if 0 < position <= music_player.queue.size():
            title = music_player.queue(position).title
            sentences = {
                "initial":  "Delet this?",
                "yes":      f"Deleted **{title}** from queue.",
                "no":       "Cancelled deleting.",
                "timeout":  "Timeout, cancelled deleting."
            }
            check = await ctx.yes_no_prompt(sentences)
            if check:
                await music_player.queue.delete(position-1)
        else:
            await ctx.send("Position out of range.")

    @music.command()
    async def purge(self, ctx):
        '''
            `>>music purge`
            Purge all songs from queue.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        sentences = {
            "initial":  f"Purge queue?",
            "yes":      "Queue purged.",
            "no":       "Cancelled purging.",
            "timeout":  "Timeout, cancelled purging."
        }
        check = await ctx.yes_no_prompt(sentences)
        if check:
            await music_player.queue.purge()

    @music.command()
    async def export(self, ctx, *, name="playlist"):
        '''
            `>>music export <optional: name>`
            Export current queue to a JSON file.
            If no name is provided, default name `playlist` is used instead.
        '''
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
        '''
            `>>music import`
            Import JSON playlist file to queue.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        msg = ctx.message
        if not msg.attachments:
            await msg.add_reaction("\U0001f504")
            try:
                msg = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.author.id and m.attachments, timeout=120)
            except asyncio.TimeoutError:
                return
            finally:
                try:
                    await ctx.message.clear_reactions()
                except:
                    pass
        bytes_ = BytesIO()
        await msg.attachments[0].save(bytes_)
        playlist = json.loads(bytes_.getvalue().decode("utf-8"))
        if isinstance(playlist, list):
            if len(playlist) + music_player.queue.size() > 1000:
                return await ctx.send("Too many entries.")
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

    @music.command(aliases=["p"])
    async def playlist(self, ctx, *, name=None):
        '''
            `>>music playlist <optional: name>`
            Search Youtube for a playlist and put it in queue.
            If <name> starts with `-r` or `-random` flag then the playlist is put in in random order.
            If no name is provided, the current queue is displayed instead.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        if not name:
            embeds = self.current_queue_info(music_player)
            return await ctx.embed_page(embeds)
        if name.startswith("-random "):
            shuffle = True
            name = name[8:]
        elif name.startswith("-r "):
            shuffle = True
            name = name[3:]
        else:
            shuffle = False
        results = await self.bot.run_in_lock(self.lock, self.youtube_search, name, "playlist")
        stuff = "\n\n".join([
            f"`{i+1}:` **[{utils.discord_escape(p['snippet']['title'])}](https://www.youtube.com/playlist?list={p['id']['playlistId']})**\n      By: {p['snippet']['channelTitle']}"
            for i,p in enumerate(results)
        ])
        embed = discord.Embed(title="\U0001f3b5 Playlist search result: ", description=f"{stuff}\n\n`<>:` cancel", colour=discord.Colour.green())
        embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
        await ctx.send(embed=embed)
        index = await ctx.wait_for_choice(max=len(results))
        if index is None:
            return
        else:
            result = results[index]
        async with ctx.typing():
            items = await self.bot.run_in_lock(self.lock, self.youtube_playlist_items, ctx.message, result["id"]["playlistId"])
            if len(items) + music_player.queue.size() > 1000:
                return await ctx.send("Too many entries.")
            if shuffle:
                random.shuffle(items)
                add_text = " in random position"
            else:
                add_text = ""
            await music_player.queue.put_many(items)
            await ctx.send(f"Added {len(items)} songs to queue{add_text}.")

    def youtube_video_info(self, url):
        video_id = youtube_match.match(url).group(1)
        result = self.youtube.videos().list(part='snippet,contentDetails,statistics', id=video_id).execute()
        video = result["items"][0]
        return video

    @music.command(aliases=["i"])
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def info(self, ctx, stuff="0"):
        '''
            `>>music info <optional: either queue position or youtube link>`
            Display video info.
            If no argument is provided, the currently playing song is used instead.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        try:
            position = int(stuff)
        except:
            url = stuff.strip("<>")
        else:
            position -= 1
            if position < 0:
                song = music_player.current_song
                if not song:
                    return await ctx.send("No song is currently playing.")
            elif position < music_player.queue.size():
                song = music_player.queue(position)
            else:
                return await ctx.send("Position out of range.")
            url = song.url
        video = await self.bot.run_in_lock(self.lock, self.youtube_video_info, url)
        snippet = video["snippet"]
        description = utils.unifix(snippet.get("description", "None")).strip()
        description_page = utils.split_page(description, 500)
        max_page = len(description_page)
        embeds = []
        for index, desc in enumerate(description_page):
            embed = discord.Embed(title=f"\U0001f3b5 {snippet['title']}", url=url, colour=discord.Colour.green())
            embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
            embed.add_field(name="Uploader", value=f"[{snippet['channelTitle']}](https://www.youtube.com/channel/{snippet['channelId']})")
            embed.add_field(name="Date", value=snippet["publishedAt"][:10])
            embed.add_field(name="Duration", value=f"\U0001f552 {video['contentDetails'].get('duration', '0s')[2:].lower()}")
            embed.add_field(name="Views", value=f"\U0001f441 {int(video['statistics'].get('viewCount', 0)):n}")
            embed.add_field(name="Likes", value=f"\U0001f44d {int(video['statistics'].get('likeCount', 0)):n}")
            embed.add_field(name="Dislikes", value=f"\U0001f44e {int(video['statistics'].get('dislikeCount', 0)):n}")
            embed.add_field(name="Description", value=f"{desc}\n\n(Page {index+1}/{max_page})", inline=False)
            for key in ("maxres", "standard", "high", "medium", "default"):
                value = snippet["thumbnails"].get(key, None)
                if value is not None:
                    embed.set_image(url=value["url"])
                    break
            embeds.append(embed)
        await ctx.embed_page(embeds)

    @music.command(aliases=["t"])
    async def toggle(self, ctx):
        '''
            `>>music toggle`
            Toggle play/pause.
        '''
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
        '''
            `>>music forward <optional: seconds>`
            Fast forward. The limit is 59 seconds.
            If no argument is provided, fast forward by 10 seconds.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        song = music_player.current_song
        if song:
            if music_player.voice_client.is_playing():
                if 0 < seconds < 60:
                    tbefore = song.time_elapsed()
                    safter = int(song.music.original.fast_forward(seconds*50) * 0.02)
                    tafter = (safter//3600, safter%3600//60, safter%60)
                    await ctx.send(f"Forward from {tbefore[0]:02}:{tbefore[1]:02}:{tbefore[2]:02} to {tafter[0]:02}:{tafter[1]:02}:{tafter[2]:02}.")
                else:
                    await ctx.send("Fast forward time must be between 1 and 59 seconds.")
            else:
                await ctx.send("Nothing is playing right now, oi.")
        else:
            await ctx.send("No song is currently playing.")

    @music.command(aliases=["channel"])
    async def setchannel(self, ctx):
        '''
            `>>music setchannel`
            Set the current channel as song announcement channel.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        music_player.channel = ctx.channel
        await ctx.confirm()

    @music.command(aliases=["ai"])
    async def autoinfo(self, ctx):
        '''
            `>>music autoinfo`
            Automatic info display.
            Display channel is the current channel that this command is invoked in, and paging is associated with song requestor.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        music_player.auto_info = ctx.message
        await ctx.confirm()

    @music.command(aliases=["mi"])
    async def manualinfo(self, ctx):
        '''
            `>>music manualinfo`
            Manual info display.
        '''
        music_player = await self.get_music_player(ctx.guild.id)
        music_player.auto_info = None
        await ctx.confirm()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Music(bot))
