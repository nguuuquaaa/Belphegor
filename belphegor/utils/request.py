import aiohttp
import asyncio
import os
from . import config

_lock = asyncio.Lock()
_loop = asyncio.get_event_loop()

async def fetch(session, url, **options):
    headers = options.pop("headers", {"User-Agent": config.USER_AGENT})
    async with session.get(url, headers=headers, **options) as response:
        return await response.read()

async def download(session, url, path, **options):
    async with _lock:
        headers = options.pop("headers", {"User-Agent": config.USER_AGENT})
        async with session.get(url, headers=headers, **options) as response:
            with open(path, "wb") as file:
                while True:
                    chunk = await response.content.read(config.CHUNK_SIZE)
                    if chunk:
                        file.write(chunk)
                    else:
                        return True
                        break
