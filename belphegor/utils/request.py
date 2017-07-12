import aiohttp

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.read()

async def download(session, url, path):
    async with session.get(url) as response:
        bytes_ = await response.read()
        with open(path, "wb+") as file:
            file.write(bytes_)
        return bytes_
            
