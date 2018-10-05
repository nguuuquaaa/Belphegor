import discord
from discord.ext import commands
from .utils import config, checks
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
        del self.bot.error_hook

    def set_error_handle(self):
        self.old_on_error = self.bot.on_error

        async def new_on_error(event, *args, **kwargs):
            etype, e, etb = sys.exc_info()
            if not isinstance(e, discord.Forbidden):
                prt_err = "".join(traceback.format_exception(etype, e, etb, 5))
                await self.error_hook.execute(f"```\nIgnoring exception in event {event}:\n{prt_err}\n```")

        self.bot.on_error = new_on_error

    async def get_wh(self):
        ch = self.bot.get_channel(config.LOG_CHANNEL_ID)
        self.error_hook = (await ch.webhooks())[0]
        self.bot.error_hook = self.error_hook

    async def on_command_error(self, ctx, error):
        ignored = (commands.DisabledCommand, commands.CommandNotFound, commands.UserInputError, commands.CommandOnCooldown)
        if isinstance(error, commands.CheckFailure):
            if isinstance(error, (checks.CheckFailure, commands.NotOwner, commands.NoPrivateMessage)):
                await ctx.send(error, delete_after=30)
        elif isinstance(error, commands.CommandInvokeError):
            error = error.original
            if isinstance(error, OverflowError):
                await ctx.send("Input number too big. You sure really need it?")
            elif isinstance(error, discord.Forbidden):
                await ctx.send(error)
            else:
                prt_err = "".join(traceback.format_exception(type(error), error, error.__traceback__, 5))
                await ctx.send(
                    "Unexpected error. Oops (ᵒ ڡ <)๑⌒☆\n"
                    "If you see this message, it means there's a bug in the code.\n"
                    "Please wait for a while for the owner to fix.",
                    delete_after=30
                )
                await self.error_hook.execute(f"```\nIgnoring exception in command {ctx.command}:\n{prt_err}\n```")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Argument missing. You sure know what this command does?", delete_after=30)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Bad arguments. You sure read command description?", delete_after=30)
        elif isinstance(error, ignored):
            pass
        else:
            prt_err = "".join(traceback.format_exception(type(error), error, None))
            await self.error_hook.execute(f"```\nUnexpected error:\n{prt_err}\n```")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(ErrorHandle(bot))
