import discord
from discord.ext import commands
from .utils import config
import sys
import traceback

#==================================================================================================================================================

class ErrorHandle:
    def __init__(self, bot):
        self.bot = bot
        self.set_error_handle()
        bot.loop.create_task(self.get_wh())

    def __unload(self):
        self.bot.on_error = self.old_on_error

    def set_error_handle(self):
        self.old_on_error = self.bot.on_error

        async def new_on_error(event, *args, **kwargs):
            etype, e, etb = sys.exc_info()
            prt_err = "".join(traceback.format_exception(etype, e, etb, 5))
            await self.error_hook.execute(f"```\nIgnoring exception in event {event}:\n{prt_err}\n```")

        self.bot.on_error = new_on_error

    async def get_wh(self):
        ch = self.bot.get_channel(config.LOG_CHANNEL_ID)
        self.error_hook = (await ch.webhooks())[0]

    async def on_command_error(self, ctx, error):
        ignored = (commands.DisabledCommand, commands.CheckFailure, commands.CommandNotFound, commands.UserInputError)
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
            prt_err = "".join(traceback.format_exception(type(error), error, error.__traceback__, 5))
            await ctx.send("Unexpected error. Oops (ᵒ ڡ <)๑⌒☆", delete_after=30)
            await self.error_hook.execute(f"```\nIgnoring exception in command {ctx.command}:\n{prt_err}\n```")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Argument missing. You sure read command description in detail?", delete_after=30)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Bad arguments. You sure read command description in detail?", delete_after=30)
        elif isinstance(error, commands.CommandNotFound):
            pass
        else:
            prt_err = "".join(traceback.format_exception(type(error), error, None))
            await self.error_hook.execute(f"```\nIgnoring exception in command {ctx.command}:\n{prt_err}\n```")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(ErrorHandle(bot))
