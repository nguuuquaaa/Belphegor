import discord
from discord.ext import commands
from . import checks, format
import multidict
import functools
from yarl import URL

#==================================================================================================================================================

class MultiDict(multidict.MultiDict):
    def geteither(self, *keys, default=None):
        for key in keys:
            try:
                value = self.getone(key)
            except KeyError:
                continue
            else:
                return value
        else:
            return default

    def getalltext(self, key, *, default="", delimiter=" "):
        try:
            temp = self.getall(key)
        except KeyError:
            return default
        else:
            return delimiter.join((str(t) for t in temp))

    def to_default_dict(self):
        ret = {}
        for key, value in self.items():
            rv = ret.get(key, [])
            rv.append(value)
            ret[key] = rv
        return ret

EMPTY = MultiDict()
_quotes = commands.view._quotes
_all_quotes = set((*_quotes.keys(), *_quotes.values()))
_delimiters = _all_quotes | set(("=",))

def _check_char(c):
    return c.isspace() or c in _delimiters

#==================================================================================================================================================

class KeyValue(commands.Converter):
    def __init__(self, conversion={}, *, escape=False, clean=True, multiline=True):
        self.escape = escape
        if clean:
            self.clean = format.clean_codeblock
        else:
            self.clean = str.strip
        c = {}
        for key, value in conversion.items():
            if isinstance(key, tuple):
                for k in key:
                    c[k] = value
            else:
                c[key] = value
        self.conversion = c
        self.multiline = multiline

    async def convert(self, ctx, argument):
        text = self.clean(argument)
        ret = MultiDict()

        async def resolve(key, value):
            if self.escape:
                value = value.encode("raw_unicode_escape").decode("unicode_escape")
            conv = self.conversion.get(key)
            if conv:
                value = await ctx.command.do_conversion(ctx, conv, value, key)
            ret.add(key, value)

        if self.multiline:
            for line in text.splitlines():
                line = line.strip()
                if line:
                    key, sep, value = line.partition("=")
                    if sep:
                        key, value = key.strip(), value.strip()
                    else:
                        key, value = "", key.strip()
                    await resolve(key, value)
        else:
            wi = format.split_iter(text, check=_check_char)
            key = ""
            prev_word = ""

            while True:
                try:
                    word = next(wi)
                except StopIteration:
                    break

                if word == "=":
                    if key:
                        prev_word = prev_word + "="
                    else:
                        key = prev_word
                        prev_word = ""
                elif word in _quotes:
                    quote_close = _quotes[word]
                    quote_words = []
                    escape = False
                    while True:
                        try:
                            w = next(wi)
                        except StopIteration:
                            raise commands.BadArgument("No closing quote.")
                        else:
                            if escape:
                                quote_words.append(w)
                                escape = False
                            elif w == quote_close:
                                await resolve(key, "".join(quote_words))
                                key = ""
                                prev_word = ""
                                break
                            else:
                                if w == "\\":
                                    escape = True
                                quote_words.append("\\")
                elif not word.isspace():
                    prev_word = prev_word + word
                else:
                    await resolve(key, prev_word)
                    key = ""
                    prev_word = ""
            if prev_word:
                await resolve(key, prev_word)

        return ret

#==================================================================================================================================================

class URLConverter(commands.Converter):
    def __init__(self, schemes=["http", "https"]):
        self.schemes = schemes
        self._accept_string = "/".join(schemes)

    async def convert(self, ctx, argument):
        argument = argument.lstrip("<").rstrip(">")
        url = URL(argument)
        if url.scheme in self.schemes:
            if url.scheme and url.host and url.path:
                return url
            else:
                raise commands.BadArgument("Malformed URL.")
        else:
            raise checks.CustomError(f"This command accepts url with scheme {self._accept_string} only.")

#==================================================================================================================================================

def _transfer_modding(from_, to_):
    try:
        ctgr = from_.category
    except AttributeError:
        pass
    else:
        to_.brief = from_.brief
        to_.category = from_.category
        to_.field = from_.field
        to_.paragraph = from_.paragraph

#modding.help hax, so new attributes are preserved when creating a commands.Cog instance
def _wrap_transfer(func):
    @functools.wraps(func)
    def new_func(self):
        ret = func(self)
        _transfer_modding(self, ret)
        return ret
    return new_func

commands.Command.copy = _wrap_transfer(commands.Command.copy)
#end hax

def help(**kwargs):
    def wrapper(command):
        command.brief = kwargs.pop("brief", None)
        command.category = kwargs.pop("category", None)
        command.field = kwargs.pop("field", "Commands")
        command.paragraph = kwargs.pop("paragraph", 0)
        return command
    return wrapper
