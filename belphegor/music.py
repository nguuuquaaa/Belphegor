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



class Buffer(queue.Queue):
    def get(self):
        with self.not_empty:
            while not len(self.queue):
                self.not_empty.wait()
            item = self.queue.popleft()
            self.not_full.notify()
            return item



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
        self.music = FFmpegWithBuffer(url, before_options="-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 2")



class MusicPlayer:
    def __init__(self, bot):
        self.bot = bot
        self.queue = asyncio.Queue()
        self.voice_client = None
        self.current_song = None
        self.player = None
        self.play_next_song = asyncio.Event()

    def ready_to_play(self, voice_client):
        self.voice_client = voice_client
        self.no_voice()
        self.player = self.bot.loop.create_task(self.play_till_eternity())

    def no_voice(self):
        try:
            self.player.cancel()
            self.player = None
        except:
            pass

    def skip(self):
        if self.voice_client.is_playing():
            self.voice_client.stop()

    async def play_till_eternity(self):
        def next_part(e):
            if e:
                print(e)
            self.current_song = None
            self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

        while True:
            self.play_next_song.clear()
            if not self.current_song:
                self.current_song = await self.queue.get()
            self.current_song.raw_update()
            await self.current_song.channel.send("Playing **{}** requested by {}.".format(self.current_song.title, self.current_song.requestor.display_name))
            self.voice_client.play(self.current_song.music, after=next_part)
            await self.play_next_song.wait()



class MusicBot:
    def __init__(self, bot):
        self.bot = bot
        self.music_players = {}

        DEVELOPER_KEY = token.youtube_key
        YOUTUBE_API_SERVICE_NAME = "youtube"
        YOUTUBE_API_VERSION = "v3"
        self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

    def get_music_player(self, guild):
        try:
            mp = self.music_players[guild.id]
            if not mp.voice_client:
                current_voice = discord.utils.find(lambda vc: vc.guild.id==guild.id, self.bot.voice_clients)
                mp.voice_client = current_voice
        except KeyError:
            mp = MusicPlayer(self.bot)
            self.music_players[guild.id] = mp
        return mp

    async def join_voice_channel(self, voice_channel):
        current_voice = discord.utils.find(lambda vc: vc.guild.id==voice_channel.guild.id, self.bot.voice_clients)
        if current_voice is None:
            voice_client = await voice_channel.connect()
        else:
            voice_client = current_voice
        mp = self.get_music_player(voice_channel.guild)
        mp.ready_to_play(voice_client)

    @commands.group(aliases=["m",])
    async def music(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @music.command(aliases=["j",])
    async def join(self, ctx):
        try:
            vc = ctx.message.author.voice.channel
            await self.join_voice_channel(vc)
            await ctx.send("{} joined {}.".format(self.bot.user.display_name, vc.name))
        except AttributeError:
            await ctx.send("You are not in a voice channel.")

    @music.command(aliases=["l",])
    async def leave(self, ctx):
        music_player = self.get_music_player(ctx.message.guild)
        music_player.no_voice()
        try:
            name = music_player.voice_client.channel.name
            await music_player.voice_client.disconnect()
            await ctx.send("{} left {}.".format(self.bot.user.display_name, name))
        except AttributeError:
            await ctx.send("{} is not in any voice channel.".format(self.bot.user.display_name))

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
        music_player = self.get_music_player(ctx.message.guild)
        if not name:
            await ctx.send("```fix\n(Playing) {}```".format(music_player.current_song.title))
            return
        else:
            results = await self.bot.loop.run_in_executor(None, self.youtube_search, name)
            await ctx.send("Search results:```fix\n{}\n<>: cancel\n```".format("\n".join([str(i+1)+": "+v["snippet"]["title"] for i,v in enumerate(results)])))
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
            song = Song(ctx.message, title , "http://www.youtube.com/watch?v="+result["id"]["videoId"])
            await music_player.queue.put(song)
            await ctx.send("Added **{}** to queue.".format(title))

    @music.command(aliases=["s",])
    async def skip(self, ctx):
        music_player = self.get_music_player(ctx.message.guild)
        music_player.skip()



def setup(bot):
    bot.add_cog(MusicBot(bot))
