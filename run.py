from discord.ext import commands
from belphegor import utils
from belphegor.utils import config, token, modding
import logging
import importlib
import asyncio
import bot
import sys

#==================================================================================================================================================

try:
    import uvloop
except:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

#==================================================================================================================================================

if __name__ == "__main__":
    while True:
        belphybot = bot.Belphegor(owner_id=config.OWNER_ID)
        belphybot.run(token.TOKEN)
        if not belphybot.restart_flag:
            break
        else:
            asyncio.set_event_loop(asyncio.new_event_loop())
            to_be_deleted = [m for m in sys.modules if m.startswith("belphegor")]
            for m in to_be_deleted:
                del sys.modules[m]
            importlib.reload(bot)

