import discord
from discord.ext import commands
import asyncio
import pafy
from .utils import request, config, token
from apiclient.discovery import build
import os
from discord.opus import Encoder as OpusEncoder
import queue
import threading

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
        thread = threading.Thread(target=self.read_buffer, args=())
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
        self._playlist = []
        self._lock = asyncio.Event()


    def put(self, item):
        self._playlist.append(item)
        self._lock.set()


    async def get(self):
        if not self._playlist:
            self._lock.clear()
            await self._lock.wait()
        return self._playlist.pop(0)

    def delete(self, position):
        return self._playlist.pop(position)

    def size(self):
        return len(self._playlist)

    def display_playlist(self):
        textout = ""
        for index, song in enumerate(self._playlist):
            textout = f"{textout}\n{index+1}. {song.title}"
        return textout

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

    def ready_to_play(self, voice_client):
        self.voice_client = voice_client
        try:
            self.player.cancel()
        except:
            pass
        self.player = self.bot.loop.create_task(self.play_till_eternity())

    def skip(self):
        if self.voice_client.is_playing():
            self.voice_client.stop()

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
                    except:
                        return
                    await self.channel.send("*\"No music? Time to sleep then. Yaaawwnnnn~~\"*")
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
        msg = await ctx.send("Connecting...")
        current_voice = discord.utils.find(lambda vc: vc.guild.id==voice_channel.guild.id, self.bot.voice_clients)
        if current_voice:
            await current_voice.disconnect()
        voice_client = await voice_channel.connect()
        mp = self.get_music_player(voice_channel.guild.id)
        mp.ready_to_play(voice_client)
        mp.channel = ctx.message.channel
        await msg.edit(content=f"{self.bot.user.display_name} joined {voice_channel.name}.")

    @music.command(aliases=["l",])
    async def leave(self, ctx):
        music_player = self.get_music_player(ctx.message.guild.id)
        try:
            name = music_player.voice_client.channel.name
            await music_player.leave_voice()
            await ctx.send(f"{self.bot.user.display_name} left {name}.")
        except AttributeError:
            await ctx.send(f"{self.bot.user.display_name} is not in any voice channel.")

    def youtube_search(self, name):
        search_response = self.youtube.search().list(q=name, part="id,snippet", maxResults=10).execute()
        videos = []
        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                videos.append(search_result)
            if len(videos) > 4:
                break
        return videos

    @music.command(aliases=["q",])
    async def queue(self, ctx, *, name:str=""):
        music_player = self.get_music_player(ctx.message.guild.id)
        if not name:
            await ctx.send(f"```fix\n(Playing) {music_player.current_song.info if music_player.current_song else 'None'}\n={music_player.queue.display_playlist()}```")
            return
        else:
            results = await self.bot.loop.run_in_executor(None, self.youtube_search, name)
            await ctx.send("Search results:```fix\n{}\n<>: cancel\n```".format('\n'.join([f"{i+1}: {v['snippet']['title']}" for i,v in enumerate(results)])))
            message = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.message.author.id)
            try:
                choose = int(message.content) - 1
                if choose in range(5):
                    result = results[choose]
                else:
                    return
            except Exception as e:
                print(e)
                return
            title = result["snippet"]["title"]
            song = Song(ctx.message, title , f"http://www.youtube.com/watch?v={result['id']['videoId']}")
            music_player.queue.put(song)
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
            message = await ctx.send(f"Delet this song number {position}?")
            e_emoji = ("\u2705", "\u274c")
            for e in e_emoji:
                await message.add_reaction(e)
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=lambda r,u:r.emoji in e_emoji and u.id==ctx.message.author.id, timeout=10)
                if reaction.emoji == "\u2705":
                    song = music_player.queue.delete(position-1)
                    await message.edit(f"Deleted **{song.title}** from queue.")
                else:
                    await message.edit(content="Cancelled deleting.")
            except asyncio.TimeoutError:
                await message.edit(content="Timeout, cancelled deleting.")
            await message.clear_reactions()
        else:
            await ctx.send("Position out of range.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(MusicBot(bot))
