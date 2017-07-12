import discord
from discord.ext import commands
from belphegor.utils import token, config
import time

belphegor = commands.Bot(command_prefix=commands.when_mentioned_or("!!", ">>", "b>"), owner_id=config.owner_id)

def load_extensions():
    with open("extensions.txt") as file:
        extensions = [e for e in file.read().splitlines() if e]
    for extension in extensions:
        try:
            belphegor.load_extension(extension)
            print("Loaded {}".format(extension))
        except Exception as e:
            print("Failed loading {}: {}".format(extension, e))

@belphegor.event
async def on_ready():
    print('Logged in as')
    print(belphegor.user.name)
    print(belphegor.user.id)
    print('------')
    time.sleep(1)
    load_extensions()
    with open(config.data_path+"\\misc\\start_time.txt", "w+") as file:
        file.write(str(time.time()))
    await belphegor.change_presence(game=discord.Game(name='with Chronos-senpai'))

if __name__ == "__main__":
    belphegor.run(token.token)
