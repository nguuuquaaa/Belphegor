import aiohttp
import asyncio
import os
from . import config, checks
import itertools
import math

#==================================================================================================================================================

_lock = asyncio.Lock()
MAX_FILE_SIZE = 1024 * 1024 * 20

#==================================================================================================================================================

async def fetch(session, url, *, max_file_size=MAX_FILE_SIZE, **options):
    headers = options.pop("headers", {"User-Agent": config.USER_AGENT})
    async with session.get(url, headers=headers, **options) as response:
        stream = response.content
        data = []
        current_size = 0
        async for chunk in stream.iter_chunked(config.CHUNK_SIZE):
            current_size += len(chunk)
            if current_size > max_file_size:
                break
            else:
                data.append(chunk)
        if stream.at_eof():
            return b"".join(data)
        else:
            raise checks.CustomError(f"File size limit is {max_file_size/1024/1024:.1f}MB.")

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
