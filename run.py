from belphegor import utils
from belphegor.utils import data_type, config, token
import logging
import importlib
import asyncio

try:
    import uvloop
except:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

#==================================================================================================================================================

if __name__ == "__main__":
    while True:
        belphybot = data_type.Belphegor(owner_id=config.OWNER_ID)
        belphybot.run(token.TOKEN)
        if not belphybot.restart_flag:
            break
        else:
            asyncio.set_event_loop(asyncio.new_event_loop())
            for m in belphybot.reload_needed:
                importlib.reload(m)
