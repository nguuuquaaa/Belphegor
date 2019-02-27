import discord
from discord.ext import commands
import asyncio
from . import utils
from .utils import config, token, data_type, checks, modding
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
import weakref
import youtube_dl
import functools

#==================================================================================================================================================

youtube_match = re.compile(r"(?:https?\:\/\/)?(?:www\.)?(?:youtube(?:-nocookie)?\.com\/\S*[^\w\s-]|youtu\.be\/)([\w-]{11})(?:[^\w\s-]|$)")
BUFFER_SIZE = 3000
MAX_PLAYLIST_SIZE = 1000

ytdl_format_options = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0"
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
ytdl_extract_info = functools.partial(ytdl.extract_info, download=False)

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
        super().__init__(*args, **kwargs)
        self._buffer = Buffer(BUFFER_SIZE)
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
    __slots__ = ("requestor", "raw_title", "title", "url", "default_volume", "index", "duration", "music")

    def __init__(self, requestor, title, url, index=0):
        self.requestor = requestor
        self.raw_title = title
        self.title = utils.discord_escape(title)
        self.url = url
        self.default_volume = 1.0
        self.index = index
        self.duration = "?"
        self.music = None

    def raw_update(self):
        try:
            data, f = self.get_stream()
        except:
            return None
        if data.get("duration"):
            d = data["duration"]
            self.duration = f"{d//3600:02}:{d%3600//60:02}:{d%60:02}"
        self.music = discord.PCMVolumeTransformer(
            FFmpegWithBuffer(
                f["url"],
                before_options="-hide_banner -nostats -loglevel 0 -reconnect 1"
            ),
            volume=self.default_volume
        )

    def get_stream(self):
        data = ytdl_extract_info(self.url)
        if not data["formats"]:
            return None
        audios = []
        others = []
        for f in data["formats"]:
            if f.get("abr"):
                audios.append(f)
            else:
                others.append(f)
        audios.sort(key=lambda x: x["abr"], reverse=True)
        others.sort(key=lambda x: x.get("tbr", 0), reverse=True)
        f = {}
        for a in audios:
            if 72 < a["abr"] < f.get("abr", 9999):
                f = a
        if not f:
            f = utils.get_element(others, lambda x: 144 < x.get("height", 0) < 720, default=utils.get_element(others, 0))
        return data, f

    def info(self):
        if self.music:
            second_elapsed = int(self.music.original.counter * 0.02)
        else:
            second_elapsed = 0
        return f"{self.title} ({second_elapsed//3600:02}:{second_elapsed%3600//60:02}:{second_elapsed%60:02} / {self.duration})"

    def time_elapsed(self):
        second_elapsed = int(self.music.original.counter * 0.02)
        return (second_elapsed//3600, second_elapsed%3600//60, second_elapsed%60)

    def to_dict(self):
        return {"requestor_id": getattr(self.requestor, "id", None), "title": self.raw_title, "url": self.url, "index": self.index}

#==================================================================================================================================================

class MusicQueue:
    __slots__ = ("playlist_data", "guild_id", "playlist", "_lock", "_not_empty", "_not_full", "next_index")

    def __init__(self, bot, guild_id, *, next_index):
        self.playlist_data = bot.db.music_playlist_data
        self.guild_id = guild_id
        self.playlist = []
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
                    self.playlist.append(s)
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
            if not len(self.playlist):
                await self._not_empty.wait()
            song = self.playlist.pop(0)
            await asyncio.shield(self.playlist_data.update_one({"guild_id": self.guild_id}, {"$pop": {"playlist": -1}, "$set": {"current_song": song.to_dict()}}))
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

    def __getitem__(self, key):
        if isinstance(key, slice):
            raise TypeError("Don't slice music queue.")
        else:
            return self.playlist[key]

    def __iter__(self):
        return iter(self.playlist)

    def __bool__(self):
        return bool(self.playlist)

    def __len__(self):
        return len(self.playlist)

    def __contains__(self, item):
        return item in self.playlist

#==================================================================================================================================================

class MusicPlayer:
    __slots__ = ("bot", "guild", "queue", "current_song", "repeat", "channel", "player", "lock", "auto_info")

    def __init__(self, bot, guild, *, initial, next_index, repeat=False):
        self.bot = bot
        self.guild = guild
        self.queue = MusicQueue(bot, guild.id, next_index=next_index)
        self.current_song = None
        self.repeat = repeat
        self.channel = None
        self.player = None
        self.lock = asyncio.Lock()
        self.queue.playlist.extend((Song(guild.get_member(s["requestor_id"]), s["title"], s["url"], s["index"]) for s in initial))
        self.auto_info = None

    def ready_to_play(self, channel):
        self.channel = channel
        self.player = weakref.ref(self.bot.loop.create_task(self.play_till_eternity()))

    def skip(self):
        if self.guild.voice_client:
            if self.guild.voice_client.is_playing():
                self.guild.voice_client.stop()
        if self.repeat is True:
            self.current_song = None

    async def leave_voice(self):
        if self.guild.voice_client:
            await asyncio.shield(self.guild.voice_client.disconnect(force=True))

    async def clear_current_song(self):
        self.current_song = None
        await asyncio.shield(self.queue.playlist_data.update_one({"guild_id": self.guild.id}, {"$set": {"current_song": None}}))

    async def set_repeat(self, mode):
        self.repeat = mode
        await self.queue.playlist_data.update_one({"guild_id": self.guild.id}, {"$set": {"repeat": mode}})

    def cancel(self):
        try:
            self.player().cancel()
        except:
            pass

    def quit(self):
        self.cancel()
        self.bot.create_task_and_count(self.leave_voice())

    async def play_till_eternity(self):
        def next_part(e):
            if e:
                print(e)
            self.bot.loop.call_soon_threadsafe(play_next_song.set)

        play_next_song = asyncio.Event()
        cmd = self.bot.get_command("music info")
        voice = self.guild.voice_client

        while True:
            play_next_song.clear()
            if not self.current_song:
                try:
                    self.current_song = await asyncio.wait_for(self.queue.get(), 120, loop=self.bot.loop)
                except asyncio.TimeoutError:
                    await self.channel.send("No music? Time to sleep then. Yaaawwnnnn~~")
                    async with self.lock:
                        return await self.leave_voice()
            await self.bot.loop.run_in_executor(None, self.current_song.raw_update)
            if self.current_song.music is None:
                title = self.current_song.title
                await self.clear_current_song()
                await self.channel.send(f"**{title}** is not available.")
            else:
                voice.play(self.current_song.music, after=next_part)
                name = utils.discord_escape(getattr(self.current_song.requestor, "display_name", "<User left server>"))
                await self.channel.send(f"Playing **{self.current_song.title}** requested by {name}.")
                if self.auto_info:
                    new_msg = copy.copy(self.auto_info)
                    new_msg.author = self.current_song.requestor or new_msg.author
                    new_ctx = await self.bot.get_context(new_msg, cls=data_type.BelphegorContext)
                    await new_ctx.invoke(cmd)
                await play_next_song.wait()
                if self.repeat is None:
                    await asyncio.shield(self.queue.put(self.current_song))
                if not self.repeat:
                    await self.clear_current_song()

            for m in voice.channel.members:
                if not m.bot:
                    break
            else:
                try:
                    member, before, after = await self.bot.wait_for("voice_state_update", check=lambda m, b, a: not m.bot and not b.channel and a.channel==voice.channel, timeout=120)
                except asyncio.TimeoutError:
                    await self.channel.send("No one's here? I'm skipping this then.")
                    async with self.lock:
                        return await self.leave_voice()

#==================================================================================================================================================

class Music(commands.Cog):
    '''
    Music is life.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.playlist_data = bot.db.music_playlist_data
        self.music_players = {}
        locale.setlocale(locale.LC_ALL, "")
        self.youtube = build("youtube", "v3", developerKey=token.GOOGLE_CLIENT_API_KEY)
        self.yt_lock = asyncio.Lock()
        self.mp_lock = asyncio.Lock()
        self.ytdl_lock = asyncio.Lock()

    def cog_unload(self):
        for mp in self.music_players.values():
            mp.quit()

    async def get_music_player(self, guild):
        async with self.mp_lock:
            mp = self.music_players.get(guild.id)
            if not mp:
                mp_data = await self.playlist_data.find_one_and_update(
                    {"guild_id": guild.id},
                    {"$setOnInsert": {"guild_id": guild.id, "next_index": 0, "playlist": [], "current_song": None, "repeat": False}},
                    return_document=ReturnDocument.AFTER,
                    upsert=True
                )
                mp = MusicPlayer(self.bot, guild, initial=mp_data["playlist"], next_index=mp_data["next_index"], repeat=mp_data["repeat"])
                cur_song = mp_data.get("current_song")
                if cur_song:
                    mp.current_song = Song(guild.get_member(cur_song["requestor_id"]), cur_song["title"], cur_song["url"], cur_song["index"])
                self.music_players[guild.id] = mp
            return mp

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == self.bot.user.id:
            if not after.channel:
                self.music_players.pop(member.guild.id).cancel()

    @modding.help(category="Music", field="Commands", paragraph=0)
    @commands.group(aliases=["m"])
    @checks.guild_only()
    async def music(self, ctx):
        '''
            `>>music`
            Base command. Does nothing by itself, but with subcommands can be used to play music.
        '''
        if ctx.invoked_subcommand is None:
            pass

    @modding.help(brief="Join voice channel and play", category="Music", field="Commands", paragraph=0)
    @music.command(aliases=["j"])
    async def join(self, ctx):
        '''
            `>>music join`
            Have Belphegor join the current voice channel you are in and play everything in queue.
            May or may not bug out when the connection is unstable. If that happens, try move her to another channel.
        '''
        try:
            voice_channel = ctx.author.voice.channel
        except AttributeError:
            msg = await ctx.send("You are not in a voice channel. Try joining one, I'm waiting.")
            try:
                member, before, after = await self.bot.wait_for("voice_state_update", check=lambda m, b, a: m.id==ctx.author.id and a.channel.guild.id==ctx.guild.id, timeout=120)
            except asyncio.TimeoutError:
                return msg.edit(content="So you don't want to listen to music? Great, I don't have to work then!")
            else:
                voice_channel = after.channel
                await msg.delete()

        music_player = await self.get_music_player(ctx.guild)
        async with music_player.lock:
            if ctx.voice_client:
                await ctx.send("I am already in a voice channel.")
            else:
                msg = await ctx.send("Connecting...")
                try:
                    await voice_channel.connect(timeout=20, reconnect=False)
                except asyncio.TimeoutError:
                    return await msg.edit(content="Cannot connect to voice. Try joining other voice channel.")

                music_player.ready_to_play(ctx.channel)
                await msg.edit(content=f"{self.bot.user.display_name} joined {voice_channel.name}.")

    @modding.help(brief="Leave voice channel", category="Music", field="Commands", paragraph=0)
    @music.command(aliases=["l"])
    async def leave(self, ctx):
        '''
            `>>music leave`
            Have Belphegor leave voice channel.
        '''
        music_player = await self.get_music_player(ctx.guild)
        async with music_player.lock:
            try:
                name = ctx.voice_client.channel.name
            except AttributeError:
                await ctx.send(f"{self.bot.user.display_name} is not in any voice channel.")
            else:
                music_player.quit()
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
            if music_player.guild.voice_client.is_playing():
                state = "\u25b6"
            else:
                state = "\u23f8"
        except AttributeError:
            state = "\u23f9"
        if music_player.repeat is None:
            repeat = "\U0001f501"
        elif music_player.repeat is True:
            repeat = "\U0001f502"
        elif music_player.repeat is False:
            repeat = ""
        try:
            current_song_info = music_player.current_song.info()
        except AttributeError:
            current_song_info = ""
        if music_player.queue:
            return utils.Paginator(
                music_player.queue, 10, separator="\n\n",
                title=f"{state}{repeat} {current_song_info}",
                description=lambda i, x: f"`{i+1}.` **[{x.title}]({x.url})**",
                colour=discord.Colour.green(),
                thumbnail_url="http://i.imgur.com/HKIOv84.png"
                )
        else:
            return discord.Embed(title=f"{state}{repeat} {current_song_info}", colour=discord.Colour.green())

    @modding.help(brief="Queue a song", category="Music", field="Commands", paragraph=1)
    @music.command(aliases=["q"])
    async def queue(self, ctx, *, name=None):
        '''
            `>>music queue <optional: name or url>`
            Search Youtube for song name then put it in queue, or immediately queue it if input is a recognized url.
            If no input is provided, the current queue is displayed instead.
            Queue is server-specific.
        '''
        music_player = await self.get_music_player(ctx.guild)
        if not name:
            i = self.current_queue_info(music_player)
            if isinstance(i, utils.Paginator):
                return await i.navigate(ctx)
            else:
                return await ctx.send(embed=i)

        if 1 + len(music_player.queue) > MAX_PLAYLIST_SIZE:
            return await ctx.send("Too many entries.")

        if name.startswith(("http://", "https://")):
            try:
                d = await self.bot.run_in_lock(self.ytdl_lock, ytdl_extract_info, name)
            except:
                await ctx.send("This url is not available.")
            else:
                if d["formats"]:
                    await music_player.queue.put(Song(ctx.message.author, d["title"], d["webpage_url"]))
                    await ctx.send(f"Added **{d['title']}** to queue.")
                else:
                    await ctx.send("Song not found.")
            finally:
                return

        results = await self.bot.run_in_lock(self.yt_lock, self.youtube_search, name)
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
            result = results[index-1]
        title = result["snippet"]["title"]
        await music_player.queue.put(Song(ctx.message.author, title, f"https://youtu.be/{result['id']['videoId']}"))
        await ctx.send(f"Added **{title}** to queue.")

    @modding.help(brief="Skip current song", category="Music", field="Commands", paragraph=3)
    @music.command(aliases=["s"])
    async def skip(self, ctx):
        '''
            `>>music skip`
            Skip current song.
        '''
        music_player = await self.get_music_player(ctx.guild)
        music_player.skip()
        await ctx.confirm()

    @modding.help(brief="Set volume", category="Music", field="Commands", paragraph=3)
    @music.command(aliases=["v"])
    async def volume(self, ctx, vol: int):
        '''
            `>>music volume <value>`
            Set volume of current song. Volume must be an integer between 0 and 200.
            Default volume is 100.
        '''
        music_player = await self.get_music_player(ctx.guild)
        if 0 <= vol <= 200:
            if music_player.current_song:
                music_player.current_song.default_volume = vol / 100
                if music_player.current_song.music:
                    music_player.current_song.music.volume = vol / 100
                await ctx.send(f"Volume for current song has been set to {vol}%.")
            else:
                await ctx.send("No song is currently playing.")
        else:
            await ctx.send("Volume must be between 0 and 200.")

    @modding.help(brief="Toggle repeat mode", category="Music", field="Commands", paragraph=3)
    @music.command(aliases=["r"])
    async def repeat(self, ctx):
        '''
            `>>music repeat`
            Toggle repeat mode.
            \U000025b6 - Off, play normally
            \U0001f502 - Repeat one song
            \U0001f501 - Repeat playlist
        '''
        music_player = await self.get_music_player(ctx.guild)
        _loop = self.bot.loop
        modes = ("\U000025b6", "\U0001f502", "\U0001f501")
        for m in modes:
            _loop.create_task(ctx.message.add_reaction(m))
        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=lambda r, u: r.emoji in modes and u.id==ctx.author.id, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send("Cancelled changing repeat mode.")
        else:
            if reaction.emoji == modes[0]:
                await music_player.set_repeat(False)
                await ctx.send("Repeat mode has been turned off.")
            elif reaction.emoji == modes[1]:
                await music_player.set_repeat(True)
                await ctx.send("Repeat mode has been set to one song repeat.")
            else:
                await music_player.set_repeat(None)
                await ctx.send("Repeat mode has been set to playlist repeat.")
        finally:
            await ctx.message.clear_reactions()

    @modding.help(brief="Delete a song from queue", category="Music", field="Commands", paragraph=1)
    @music.command(aliases=["d"])
    async def delete(self, ctx, position: int):
        '''
            `>>music delete <position>`
            Delete a song from queue.
        '''
        music_player = await self.get_music_player(ctx.guild)
        queue = music_player.queue
        position -= 1
        if 0 <= position < len(queue):
            title = queue[position].title
            sentences = {
                "initial":  "Delet this?",
                "yes":      f"Deleted **{title}** from queue.",
                "no":       "Cancelled deleting.",
                "timeout":  "Timeout, cancelled deleting."
            }
            check = await ctx.yes_no_prompt(sentences)
            if check:
                await queue.delete(position)
        else:
            await ctx.send("Position out of range.")

    @modding.help(brief="Delete all songs from queue", category="Music", field="Commands", paragraph=1)
    @music.command()
    async def purge(self, ctx):
        '''
            `>>music purge`
            Purge all songs from queue.
        '''
        music_player = await self.get_music_player(ctx.guild)
        sentences = {
            "initial":  f"Purge queue?",
            "yes":      "Queue purged.",
            "no":       "Cancelled purging.",
            "timeout":  "Timeout, cancelled purging."
        }
        check = await ctx.yes_no_prompt(sentences)
        if check:
            await music_player.queue.purge()

    @modding.help(brief="Export current queue to JSON file", category="Music", field="Commands", paragraph=4)
    @music.command()
    async def export(self, ctx, *, name="playlist"):
        '''
            `>>music export <optional: name>`
            Export current queue to a JSON file.
            If no name is provided, default name `playlist` is used instead.
        '''
        music_player = await self.get_music_player(ctx.guild)
        jsonable = []
        if music_player.current_song:
            jsonable.append({"title": music_player.current_song.title, "url": music_player.current_song.url})
        for song in music_player.queue:
            jsonable.append({"title": song.title, "url": song.url})
        bytes_ = json.dumps(jsonable, indent=4, ensure_ascii=False).encode("utf-8")
        await ctx.send(file=discord.File(bytes_, f"{name}.json"))

    @modding.help(brief="Import JSON playlist", category="Music", field="Commands", paragraph=4)
    @music.command(name="import")
    async def music_import(self, ctx):
        '''
            `>>music import`
            Import JSON playlist file to queue.
        '''
        music_player = await self.get_music_player(ctx.guild)
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
            if len(playlist) + len(music_player.queue) > MAX_PLAYLIST_SIZE:
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

    @modding.help(brief="Queue a playlist", category="Music", field="Commands", paragraph=1)
    @music.command(aliases=["p"])
    async def playlist(self, ctx, *, name=None):
        '''
            `>>music playlist <optional: -r or -random flag> <optional: name>`
            Search Youtube for a playlist and put it in queue.
            If random flag is provided then the playlist is put in in random order.
            If no name is provided, the current queue is displayed instead.
        '''
        music_player = await self.get_music_player(ctx.guild)
        if not name:
            i = self.current_queue_info(music_player)
            if isinstance(i, utils.Paginator):
                return await i.navigate(ctx)
            else:
                return await ctx.send(embed=i)
        if name.startswith("-random "):
            shuffle = True
            name = name[8:]
        elif name.startswith("-r "):
            shuffle = True
            name = name[3:]
        else:
            shuffle = False
        results = await self.bot.run_in_lock(self.yt_lock, self.youtube_search, name, "playlist")
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
            result = results[index-1]
        items = await self.bot.run_in_lock(self.yt_lock, self.youtube_playlist_items, ctx.message, result["id"]["playlistId"])
        if len(items) + len(music_player.queue) > MAX_PLAYLIST_SIZE:
            return await ctx.send("Too many entries.")
        if shuffle:
            random.shuffle(items)
            add_text = " in random position"
        else:
            add_text = ""
        await music_player.queue.put_many(items)
        await ctx.send(f"Added {len(items)} songs to queue{add_text}.")

    def youtube_video_info(self, video_id):
        result = self.youtube.videos().list(part='snippet,contentDetails,statistics', id=video_id).execute()
        video = result["items"][0]
        return video

    @modding.help(brief="Display video info", category="Music", field="Commands", paragraph=2)
    @music.command(aliases=["i"])
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def info(self, ctx, stuff="0"):
        '''
            `>>music info <optional: either queue position or youtube link>`
            Display video info.
            If no argument is provided, the currently playing song (position 0) is used instead.
        '''
        try:
            position = int(stuff)
        except:
            url = stuff.strip("<>")
        else:
            music_player = await self.get_music_player(ctx.guild)
            position -= 1
            if position < 0:
                song = music_player.current_song
                if not song:
                    return await ctx.send("No song is currently playing.")
            elif 0 <= position < len(music_player.queue):
                song = music_player.queue[position]
            else:
                return await ctx.send("Position out of range.")
            url = song.url
        m = youtube_match.match(url)
        if not m:
            return await ctx.send("Info can only be used with youtube url.")

        video = await self.bot.run_in_lock(self.yt_lock, self.youtube_video_info, m.group(1))
        snippet = video["snippet"]
        stat = video["statistics"]
        description = utils.unifix(snippet.get("description", "None")).strip()
        description_page = utils.split_page(description, 500)

        info_with_desc = []
        info_without_desc = []
        base_info = (
            ("Uploader",    f"[{snippet['channelTitle']}](https://www.youtube.com/channel/{snippet['channelId']})", True),
            ("Date",        snippet["publishedAt"][:10],                                                            True),
            ("Duration",    f"\U0001f552 {video['contentDetails'].get('duration', '0s')[2:].lower()}",              True),
            ("Views",       f"\U0001f441 {int(stat.get('viewCount', 0)):n}",                                        True),
            ("Likes",       f"\U0001f44d {int(stat.get('likeCount', 0)):n}",                                        True),
            ("Dislikes",    f"\U0001f44e {int(stat.get('dislikeCount', 0)):n}",                                     True)
        )
        for i in range(len(description_page)):
            info_with_desc.extend(base_info)
            info_without_desc.extend(base_info)
            info_with_desc.append(("Description", description_page[i], False))
            info_without_desc.append((None, None, None))
        for key in ("maxres", "standard", "high", "medium", "default"):
            value = snippet["thumbnails"].get(key, None)
            if value is not None:
                image_url = value["url"]
                break

        paging = utils.Paginator(
            info_without_desc, 7, page_display=False,
            title=f"\U0001f3b5 {snippet['title']}",
            url=url,
            colour=discord.Colour.green(),
            fields=lambda i, x: (x[0], x[1], x[2]),
            thumbnail_url="http://i.imgur.com/HKIOv84.png",
            image_url=image_url
        )

        paging.saved_container = info_with_desc

        def switch():
            paging.page_display = not paging.page_display
            paging.container, paging.saved_container = paging.saved_container, paging.container
            paging.render_data["image_url"] = None if paging.render_data["image_url"] else image_url
            return paging.render()

        paging.set_action("\U0001f1e9", switch)
        await paging.navigate(ctx)

    @modding.help(brief="Toggle play/pause", category="Music", field="Commands", paragraph=3)
    @music.command(aliases=["t"])
    async def toggle(self, ctx):
        '''
            `>>music toggle`
            Toggle play/pause.
            Should not pause for too long (hours), or else Youtube would complain.
        '''
        music_player = await self.get_music_player(ctx.guild)
        vc = ctx.voice_client
        if vc:
            if vc.is_paused():
                vc.resume()
                await ctx.send("Resumed playing.")
            elif vc.is_playing():
                vc.pause()
                await ctx.send("Paused.")

    @modding.help(brief="Fast forward", category="Music", field="Commands", paragraph=3)
    @music.command(aliases=["f"])
    async def forward(self, ctx, seconds: int=10):
        '''
            `>>music forward <optional: seconds>`
            Fast forward. The limit is 59 seconds.
            If no argument is provided, fast forward by 10 seconds.
        '''
        music_player = await self.get_music_player(ctx.guild)
        song = music_player.current_song
        if song:
            if ctx.voice_client:
                if ctx.voice_client.is_playing():
                    if 0 < seconds < 60:
                        tbefore = song.time_elapsed()
                        safter = int(song.music.original.fast_forward(seconds*50) * 0.02)
                        tafter = (safter//3600, safter%3600//60, safter%60)
                        await ctx.send(f"Forward from {tbefore[0]:02}:{tbefore[1]:02}:{tbefore[2]:02} to {tafter[0]:02}:{tafter[1]:02}:{tafter[2]:02}.")
                    else:
                        await ctx.send("Fast forward time must be between 1 and 59 seconds.")
                    return

        await ctx.send("Nothing is playing right now, oi.")

    @modding.help(brief="Change notifying channel", category="Music", field="Commands", paragraph=4)
    @music.command(aliases=["channel"])
    async def setchannel(self, ctx):
        '''
            `>>music setchannel`
            Set the current channel as song announcement channel.
        '''
        music_player = await self.get_music_player(ctx.guild)
        music_player.channel = ctx.channel
        await ctx.confirm()

    @modding.help(brief="Toggle auto info display", category="Music", field="Commands", paragraph=2)
    @music.command(aliases=["ai"])
    async def toggleautoinfo(self, ctx):
        '''
            `>>music autoinfo`
            Automatic info display.
            Display channel is the current channel that this command is invoked in, and paging is associated with song requestor.
            This option is reset after each session.
        '''
        music_player = await self.get_music_player(ctx.guild)
        if music_player.auto_info is None:
            music_player.auto_info = ctx.message
            await ctx.send("Auto-info mode is on.")
        else:
            music_player.auto_info = None
            await ctx.send("Auto-info mode is off.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Music(bot))
