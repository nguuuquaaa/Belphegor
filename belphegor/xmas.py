import discord
from discord.ext import commands
from . import utils
from .utils import config, token
from PIL import Image, ImageDraw
from io import BytesIO
import random

HAT_IMAGE = [Image.open(f"{config.DATA_PATH}/santa_hat/r_hat_{number+1}.png") for number in range(8)]

#==================================================================================================================================================

class XmasSpecial:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def santahat(self, ctx, direction="r", member: discord.Member=None):
        if not member:
            member = ctx.author
        if direction[0].lower() in ("l", "r"):
            direction = direction[0]
        else:
            return
        async with ctx.typing():
            bytes_ = await utils.fetch(self.bot.session, member.avatar_url_as(static_format="png"))

            def image_process():
                base_img = Image.open(BytesIO(bytes_))
                width, height = base_img.size
                min_size = min(width, height)
                hat = random.choice(HAT_IMAGE)
                if direction == "l":
                    hat = hat.transpose(Image.FLIP_LEFT_RIGHT)
                resized_hat = hat.resize((min_size, min_size), resample=Image.HAMMING)
                base_img.paste(resized_hat, (0, 0), resized_hat)
                pic_bytes = BytesIO()
                base_img.save(pic_bytes, format="png")
                return pic_bytes

            result = await self.bot.loop.run_in_executor(None, image_process)
            await ctx.send(file=discord.File(result.getvalue(), filename="santa_hat.png"))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(XmasSpecial(bot))
