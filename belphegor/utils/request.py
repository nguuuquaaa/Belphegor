import aiohttp
import asyncio
import os
from . import config, checks
import itertools
import math
import functools

#==================================================================================================================================================

MAX_FILE_SIZE = 1024 * 1024 * 20
TIMEOUT = 20
CHUNK_SIZE = 512 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36"

_lock = asyncio.Lock()

#==================================================================================================================================================

def _error_handle(func):
    @functools.wraps(func)
    async def new_func(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.TimeoutError:
            raise checks.CustomError("Cannot retrieve file. Please try again.")
        except aiohttp.InvalidURL:
            raise checks.CustomError("Invalid URL.")
    return new_func

@_error_handle
async def fetch(session, url, *, max_file_size=MAX_FILE_SIZE, timeout=TIMEOUT, **options):
    headers = options.pop("headers", {"User-Agent": USER_AGENT})
    async with session.get(url, headers=headers, timeout=timeout, **options) as response:
        stream = response.content
        data = []
        current_size = 0
        async for chunk in stream.iter_chunked(CHUNK_SIZE):
            current_size += len(chunk)
            if current_size > max_file_size:
                break
            else:
                data.append(chunk)
        if stream.at_eof():
            return b"".join(data)
        else:
            raise checks.CustomError(f"File size limit is {max_file_size/1024/1024:.1f}MB.")

@_error_handle
async def download(session, url, path, *, timeout=TIMEOUT, **options):
    async with _lock:
        headers = options.pop("headers", {"User-Agent": USER_AGENT})
        async with session.get(url, headers=headers, timeout=timeout, **options) as response:
            with open(path, "wb") as f:
                stream = response.content
                async for chunk in stream.iter_chunked(CHUNK_SIZE):
                    f.write(chunk)
                else:
                    return True
