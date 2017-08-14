import discord
from discord.ext import commands
import asyncio
import pafy
from .utils import request, config, token
from apiclient.discovery import build
from discord.opus import Encoder as OpusEncoder
import queue
from threading import Thread
from io import BytesIO
import json

#==================================================================================================================================================

class Buffer(queue.Queue):
    def get(self):
        with self.not_empty:
            if not self.queue:
                self.not_empty.wait()
            item = self.queue.popleft()
            self.not_full.notify()
            return item

#==================================================================================================================================================

class FFmpegWithBuffer(discord.FFmpegPCMAudio):
    def __init__(self, *args, **kwargs):
        discord.FFmpegPCMAudio.__init__(self, *args, **kwargs)

        self._buffer = Buffer(3000)
        thread = Thread(target=self.read_buffer, args=())
        thread.daemon = True
        thread.start()

    def read(self):
        return self._buffer.get()

    def read_buffer(self):
        while True:
            ret = self._stdout.read(OpusEncoder.FRAME_SIZE)
            if len(ret) != OpusEncoder.FRAME_SIZE:
                self._buffer.put(b'')
                return
            self._buffer.put(ret)

#==================================================================================================================================================

class Song:
    def __init__(self, message, title, url):
        self.requestor = message.author
        self.channel = message.channel
        self.title = title
        self.url = url

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
        self.music = discord.PCMVolumeTransformer(FFmpegWithBuffer(url, before_options="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 2"), volume=1)

    @property
    def info(self):
        return f"{self.title} ({self.duration})"

#==================================================================================================================================================

class Playlist():
    def __init__(self):
        self.playlist = []
        self._lock = asyncio.Event()

    def put(self, item):
        self.playlist.append(item)
        self._lock.set()

    async def get(self):
        if not self.playlist:
            self._lock.clear()
            await self._lock.wait()
        return self.playlist.pop(0)

    def delete(self, position):
        return self.playlist.pop(position)

    def size(self):
        return len(self.playlist)

    def display_playlist(self):
        playlist = []
        for index, song in enumerate(self.playlist):
            if len(song.title) > 65:
                ttl = f"{song.title[:65]}..."
            else:
                ttl = song.title
            playlist.append(f"{index+1}. [{ttl}]({song.url})")
        return playlist

#==================================================================================================================================================

class MusicPlayer:
    def __init__(self, bot):
        self.bot = bot
        self.queue = Playlist()
        self.voice_client = None
        self.current_song = None
        self.play_next_song = asyncio.Event()
        self.repeat = False
        self.channel = None
        self.player = None
        self.lock = asyncio.Lock()

    def ready_to_play(self, voice_client):
        self.voice_client = voice_client
        self.player = self.bot.loop.create_task(self.play_till_eternity())

    def skip(self):
        if self.voice_client.is_playing():
            self.voice_client.stop()
            self.current_song = None

    def _next_part(self, e):
        if e:
            print(e)
        if not self.repeat:
            self.current_song = None
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def leave_voice(self):
        self.player = None
        self.repeat = False
        await self.voice_client.disconnect()
        self.voice_client = None

    async def play_till_eternity(self):
        while True:
            self.play_next_song.clear()
            if not self.current_song:
                try:
                    self.current_song = await asyncio.wait_for(self.queue.get(), 60, loop=self.bot.loop)
                except asyncio.TimeoutError:
                    try:
                        await self.leave_voice()
                        await self.channel.send("*\"No music? Time to sleep then. Yaaawwnnnn~~\"*")
                        return
                    except:
                        return
                except:
                    return
            await self.bot.loop.run_in_executor(None, self.current_song.raw_update)
            self.voice_client.play(self.current_song.music, after=self._next_part)
            await self.current_song.channel.send(f"Playing **{self.current_song.title}** requested by {self.current_song.requestor.display_name}.")
            await self.play_next_song.wait()

#==================================================================================================================================================

class MusicBot:
    def __init__(self, bot):
        self.bot = bot
        self.music_players = {}

        DEVELOPER_KEY = token.youtube_key
        YOUTUBE_API_SERVICE_NAME = "youtube"
        YOUTUBE_API_VERSION = "v3"
        self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

    def get_music_player(self, guild_id):
        try:
            mp = self.music_players[guild_id]
        except KeyError:
            mp = MusicPlayer(self.bot)
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
            voice_channel = ctx.message.author.voice.channel
        except AttributeError:
            return await ctx.send("You are not in a voice channel.")
        music_player = self.get_music_player(voice_channel.guild.id)
        await music_player.lock.acquire()
        msg = await ctx.send("Connecting...")
        current_voice = discord.utils.find(lambda vc: vc.guild.id==voice_channel.guild.id, self.bot.voice_clients)
        if current_voice:
            await current_voice.disconnect()
        voice_client = await voice_channel.connect()
        music_player.ready_to_play(voice_client)
        music_player.channel = ctx.message.channel
        music_player.lock.release()
        await msg.edit(content=f"{self.bot.user.display_name} joined {voice_channel.name}.")

    @music.command(aliases=["l",])
    async def leave(self, ctx):
        music_player = self.get_music_player(ctx.message.guild.id)
        await music_player.lock.acquire()
        try:
            name = music_player.voice_client.channel.name
            music_player.player.cancel()
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
        music_player = self.get_music_player(ctx.message.guild.id)
        if not name:
            playlist = music_player.queue.display_playlist()
            current_song_info = music_player.current_song.info if music_player.current_song else "None"
            if playlist:
                page_data = []
                for i,p in enumerate(playlist):
                    if i%10==0:
                        page_data.append(p)
                    else:
                        page_data[i//10] = f"{page_data[i//10]}\n\n{p}"
                current_page = 0
                max_page = len(page_data)

                def data(page:int):
                    embed = discord.Embed(colour=discord.Colour.green())
                    embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
                    embed.add_field(name=f"(Playing) {current_song_info}",
                                    value=f"{page_data[page]}")
                    embed.set_footer(text=f"(Page {page+1}/{max_page})")
                    return embed

                message = await ctx.send(embed=data(0))
                possible_reactions = ("\u23ee", "\u23ed", "\u274c")
                for r in possible_reactions:
                    await message.add_reaction(r)
                while True:
                    try:
                        reaction, user = await self.bot.wait_for("reaction_add", check=lambda r,u:u.id==ctx.message.author.id and r.emoji in possible_reactions and r.message.id==message.id, timeout=20)
                    except:
                        await message.clear_reactions()
                        return
                    if reaction.emoji == "\u23ee":
                        await message.remove_reaction(reaction, user)
                        if current_page == 0:
                            continue
                        else:
                            current_page -= 1
                            await message.edit(embed=data(current_page))
                    elif reaction.emoji == "\u23ed":
                        await message.remove_reaction(reaction, user)
                        if current_page == max_page - 1:
                            continue
                        else:
                            current_page += 1
                            await message.edit(embed=data(current_page))
                    else:
                        await message.clear_reactions()
                        return
            else:
                return await ctx.send(embed=discord.Embed(title=f"(Playing) {current_song_info}", colour=discord.Colour.green()))
        else:
            results = await self.bot.loop.run_in_executor(None, self.youtube_search, name)
            embed = discord.Embed(colour=discord.Colour.green())
            embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
            embed.add_field(name="\U0001f3b5 Search result: ",
                            value="{}\n\n<>: cancel".format('\n\n'.join([f"{i+1}: [{v['snippet']['title']}](https://youtu.be/{v['id']['videoId']})" for i,v in enumerate(results)])))
            await ctx.send(embed=embed)
            message = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.message.author.id)
            try:
                choose = int(message.content) - 1
                if choose in range(5):
                    result = results[choose]
                else:
                    return
            except Exception as e:
                #print(e)
                return
            music_player.queue.put(Song(ctx.message, result["snippet"]["title"] , f"https://youtu.be/{result['id']['videoId']}"))
            await ctx.send(f"Added **{title}** to queue.")

    @music.command(aliases=["s",])
    async def skip(self, ctx):
        music_player = self.get_music_player(ctx.message.guild.id)
        music_player.skip()

    @music.command(aliases=["v",])
    async def volume(self, ctx, vol:int):
        music_player = self.get_music_player(ctx.message.guild.id)
        if 0 <= vol <= 200:
            music_player.current_song.music.volume = vol / 100
            await ctx.send(f"Volume has been set to {vol}%.")
        else:
            await ctx.send("Volume must be between 0 and 200.")

    @music.command(aliases=["r",])
    async def repeat(self, ctx):
        music_player = self.get_music_player(ctx.message.guild.id)
        if music_player.repeat:
            music_player.repeat = False
            await ctx.send("Repeat mode has been turned off.")
        else:
            music_player.repeat = True
            await ctx.send("Repeat mode has been turned on.")

    @music.command(aliases=["d",])
    async def delete(self, ctx, position:int):
        music_player = self.get_music_player(ctx.message.guild.id)
        if 0 < position <= music_player.queue.size():
            message = await ctx.send(f"Delet this?")
            e_emoji = ("\u2705", "\u274c")
            for e in e_emoji:
                await message.add_reaction(e)
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=lambda r,u:r.emoji in e_emoji and u.id==ctx.message.author.id and r.message.id==message.id, timeout=20)
                if reaction.emoji == "\u2705":
                    song = music_player.queue.delete(position-1)
                    await message.edit(content=f"Deleted **{song.title}** from queue.")
                else:
                    await message.edit(content="Cancelled deleting.")
            except asyncio.TimeoutError:
                await message.edit(content="Timeout, cancelled deleting.")
            await message.clear_reactions()
        else:
            await ctx.send("Position out of range.")

    @music.command(aliases=["e",])
    async def export(self, ctx):
        music_player = self.get_music_player(ctx.message.guild.id)
        jsonable = []
        if music_player.current_song:
            jsonable.append({"title": music_player.current_song.title, "url":music_player.current_song.url})
        for song in music_player.queue.playlist:
            jsonable.append({"title": song.title, "url":song.url})
        bytes_ = json.dumps(jsonable, indent=4, ensure_ascii=False).encode("utf-8")
        await ctx.send(file=discord.File(bytes_, "playlist.json"))

    @music.command(aliases=["i",], name="import")
    async def music_import(self, ctx):
        music_player = self.get_music_player(ctx.message.guild.id)
        msg = ctx.message
        if not ctx.message.attachments:
            await msg.add_reaction("\U0001f504")
            try:
                msg = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.message.author.id and m.attachments, timeout=120)
            except asyncio.TimeoutError:
                return await msg.clear_reactions()
            await ctx.message.clear_reactions()
        bytes_ = BytesIO()
        await msg.attachments[0].save(bytes_)
        playlist = json.loads(bytes_.getvalue().decode("utf-8"))
        for song in playlist:
            music_player.queue.put(Song(msg, song["title"] , song["url"]))
        await ctx.send(f"Added {len(playlist)} songs to queue.")

    def youtube_playlist_items(self, message, queue, playlist_id):
        number_of_items = 0
        playlist_items = self.youtube.playlistItems().list(playlistId=playlist_id, part="snippet", maxResults=50).execute()
        for song in playlist_items.get("items", None):
            queue.put(Song(message, song["snippet"]["title"], f"https://youtu.be/{song['snippet']['resourceId']['videoId']}"))
            number_of_items += 1
        while playlist_items.get("nextPageToken", None):
            playlist_items = self.youtube.playlistItems().list(playlistId=playlist_id, part="snippet", maxResults=50, pageToken=playlist_items["nextPageToken"]).execute()
            for song in playlist_items.get("items", None):
                queue.put(Song(message, song["snippet"]["title"], f"https://youtu.be/{song['snippet']['resourceId']['videoId']}"))
                number_of_items += 1
        return number_of_items

    @music.command(aliases=["p",])
    async def playlist(self, ctx, *, name):
        music_player = self.get_music_player(ctx.message.guild.id)
        results = await self.bot.loop.run_in_executor(None, self.youtube_search, name, "playlist")
        embed = discord.Embed(colour=discord.Colour.green())
        embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
        embed.add_field(name="\U0001f3b5 Search result: ",
                        value="{}\n\n<>: cancel".format('\n\n'.join([f"{i+1}: [{p['snippet']['title']}](https://www.youtube.com/playlist?list={p['id']['playlistId']})\nBy: {p['snippet']['channelTitle']}" for i,p in enumerate(results)])))
        await ctx.send(embed=embed)
        message = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.message.author.id)
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
            number_of_items = await self.bot.loop.run_in_executor(None, self.youtube_playlist_items, ctx.message, music_player.queue, result["id"]["playlistId"])
            await ctx.send(f"Added {number_of_items} songs to queue.")

    @music.command()
    async def purge(self, ctx):
        music_player = self.get_music_player(ctx.message.guild.id)
        message = await ctx.send(f"Purge queue?")
        e_emoji = ("\u2705", "\u274c")
        for e in e_emoji:
            await message.add_reaction(e)
        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=lambda r,u:r.emoji in e_emoji and u.id==ctx.message.author.id and r.message.id==message.id, timeout=20)
            if reaction.emoji == "\u2705":
                music_player.queue.playlist[:] = []
                await message.edit(content=f"Queue purged.")
            else:
                await message.edit(content="Cancelled purging.")
        except asyncio.TimeoutError:
            await message.edit(content="Timeout, cancelled purging.")
        await message.clear_reactions()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(MusicBot(bot))
