import discord
from discord.ext import commands
from belphegor.utils import token, config
import time
import asyncio

belphegor = commands.Bot(command_prefix=commands.when_mentioned_or("!!", ">>", "b>"), owner_id=config.owner_id)

@belphegor.event
async def on_ready():
    print('Logged in as')
    print(belphegor.user.name)
    print(belphegor.user.id)
    print('------')
    await asyncio.sleep(10)
    await belphegor.change_presence(game=discord.Game(name='with Chronos-senpai'))

async def load():
    await belphegor.wait_until_ready()
    with open("extensions.txt") as file:
        extensions = [e for e in file.read().splitlines() if e]
    for extension in extensions:
        try:
            belphegor.load_extension(extension)
            print(f"Loaded {extension}")
        except Exception as e:
            print(f"Failed loading {extension}: {e}")
            return await belphegor.logout()
    with open(config.data_path+"\\misc\\start_time.txt", "w+") as file:
        file.write(str(time.time()))
    print("Done")

if __name__ == "__main__":
    belphegor.loop.create_task(load())
    belphegor.run(token.token)
