import aiohttp
import asyncio
import os

lock = asyncio.Lock()
loop = asyncio.get_event_loop()

async def fetch(session, url, **options):
    async with session.get(url, **options) as response:
        return await response.read()

async def download(session, path, url, **options):
    await lock.acquire()
    if not os.path.isfile(path):
        async with session.get(url, **options) as response:
            bytes_ = await response.read()
            with open(path, "wb+") as file:
                await loop.run_in_executor(None, file.write, bytes_)
    else:
        with open(path, "rb") as file:
            bytes_ = await loop.run_in_executor(None, file.read)
    lock.release()
    return bytes_