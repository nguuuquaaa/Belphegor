from discord.ext import commands
from belphegor import utils
from belphegor.utils import config, token, modding
import logging
import importlib
import asyncio
import bot
import sys

try:
    import uvloop
except:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

#modding hax
def copy(self):
    ret = self.__class__(self.callback, **self.__original_kwargs__)
    ret._before_invoke = self._before_invoke
    ret._after_invoke = self._after_invoke
    if self.checks != ret.checks:
        ret.checks = self.checks.copy()
    if self._buckets != ret._buckets:
        ret._buckets = self._buckets.copy()
    try:
        ret.on_error = self.on_error
    except AttributeError:
        pass
    modding.transfer_modding(self, ret)
    return ret

commands.Command.copy = copy

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

