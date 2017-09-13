import aiohttp
import asyncio
import os
from . import config

lock = asyncio.Lock()
loop = asyncio.get_event_loop()

async def fetch(session, url, **options):
    headers = options.pop("headers", None)
    if headers is None:
        headers = {"User-Agent": config.USER_AGENT}
    async with session.get(url, headers=headers, **options) as response:
        return await response.read()

async def download(session, path, url, **options):
    async with lock:
        if not os.path.isfile(path):
            headers = options.pop("headers", None)
            if headers is None:
                headers = {"User-Agent": config.CHROME}
            async with session.get(url, headers=headers, **options) as response:
                bytes_ = await response.read()
                with open(path, "wb+") as file:
                    await loop.run_in_executor(None, file.write, bytes_)
        else:
            with open(path, "rb") as file:
                bytes_ = await loop.run_in_executor(None, file.read)
        return bytes_