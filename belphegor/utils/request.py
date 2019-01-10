import aiohttp
import asyncio
import os
from . import config, checks

#==================================================================================================================================================

_lock = asyncio.Lock()
MAX_FILE_SIZE = 1024 * 1024 * 20
_CHUNKS = MAX_FILE_SIZE // config.CHUNK_SIZE

#==================================================================================================================================================

async def fetch(session, url, **options):
    headers = options.pop("headers", {"User-Agent": config.USER_AGENT})
    async with session.get(url, headers=headers, **options) as response:
        stream = response.content
        data = []
        async for chunk in stream.iter_chunked(config.CHUNK_SIZE):
            data.append(chunk)
            if len(data) >= _CHUNKS:
                break
        if stream.at_eof():
            return b"".join(data)
        else:
            raise checks.CustomError("File too big. Staph.")

async def download(session, url, path, **options):
    async with _lock:
        headers = options.pop("headers", {"User-Agent": config.USER_AGENT})
        async with session.get(url, headers=headers, **options) as response:
            with open(path, "wb") as f:
                stream = response.content
                async for chunk in stream.iter_chunked(config.CHUNK_SIZE):
                    f.write(chunk)
                else:
                    return True
