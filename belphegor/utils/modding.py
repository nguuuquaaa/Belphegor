import discord
from discord.ext import commands
from . import checks, string_utils
import multidict
import functools
from yarl import URL

#==================================================================================================================================================

class SupressAttributeError(str):
    @property
    def name(self):
        return self

class BadValue(commands.CommandError):
    def __init__(self, key, value):
        self.key = key
        self.value = value

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

#==================================================================================================================================================

_quotes = commands.view._quotes
_all_quotes = set((*_quotes.keys(), *_quotes.values()))

def _greater_than(number):
    try:
        return number.set_positive_sign(True)
    except AttributeError:
        raise commands.BadArgument("Input <{number}> cannot be compared.")

def _less_than(number):
    try:
        return number.set_positive_sign(False)
    except AttributeError:
        raise commands.BadArgument("Input <{number}> cannot be compared.")

def _equal(anything):
    return anything

_standard_comparison = {
    ">": _greater_than,
    "<": _less_than,
    "=": _equal
}
_equality = {
    "=": _equal
}
_delimiters = _all_quotes | _standard_comparison.keys()

def _check_char(c):
    return c.isspace() or c in _delimiters

#==================================================================================================================================================

class Equality:
    def __init__(self, number):
        self.number = number
        self.positive_sign = None

    def set_positive_sign(self, positive_sign):
        self.positive_sign = positive_sign
        return self

    def to_query(self):
        if self.positive_sign is True:
            return {"$gt": self.number}
        elif self.positive_sign is False:
            return {"$lt": self.number}
        else:
            return self.number

class Comparison(commands.Converter):
    def __init__(self, type):
        self.type = type

    def get_comparison(self):
        return _standard_comparison

    async def convert(self, ctx, argument):
        value = await ctx.command._actual_conversion(ctx, self.type, argument, SupressAttributeError("type_conv"))
        return Equality(value)

#==================================================================================================================================================

class KeyValue(commands.Converter):
    def __init__(self, conversion={}, *, escape=False, clean=False, multiline=False):
        self.escape = escape
        if clean:
            self.clean = string_utils.clean_codeblock
        else:
            self.clean = str.strip
        self.multiline = multiline

        self.conversion = {}
        self.comparisons = {}
        for key, value in conversion.items():
            try:
                c = value.get_comparison()
            except AttributeError:
                c = _equality
            if isinstance(key, tuple):
                for k in key:
                    self.conversion[k] = value
                    self.comparisons[k] = c
            else:
                self.conversion[key] = value
                self.comparisons[key] = c

    async def convert(self, ctx, argument):
        text = self.clean(argument)
        ret = MultiDict()
        empty = {}

        async def resolve(key, value, handle):
            key = key.lower()
            orig_value = value
            if self.escape:
                value = value.encode("raw_unicode_escape").decode("unicode_escape")
            conv = self.conversion.get(key)
            if conv:
                try:
                    value = await ctx.command._actual_conversion(ctx, conv, value, SupressAttributeError(key))
                    value = handle(value)
                except commands.BadArgument:
                    raise BadValue(key, orig_value)
            ret.add(key, value)

        if self.multiline:
            for line in text.splitlines():
                line = line.strip()
                if line:
                    value = ""
                    for i, c in enumerate(line):
                        comparison = self.comparisons.get(value, _equality)
                        if c in comparison:
                            handle = comparison[c]
                            key = value
                            value = line[i+1:]
                            break
                        else:
                            value = value + c
                    else:
                        handle = _equal
                        key = ""
                        value = line
                    key, value = key.strip(), value.strip()
                    await resolve(key, value, handle)
        else:
            wi = string_utils.split_iter(text, check=_check_char)
            key = ""
            value = ""
            handle = _equal

            while True:
                try:
                    word = next(wi)
                except StopIteration:
                    break

                if key:
                    comparison = empty
                else:
                    comparison = self.comparisons.get(value, _equality)

                if word in comparison:
                    key = value
                    value = ""
                    handle = comparison[word]
                elif word in _quotes:
                    if value:
                        raise commands.BadArgument("Quote character must be placed at the start.")
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
                                value = "".join(quote_words)
                                break
                            else:
                                if w == "\\":
                                    escape = True
                                quote_words.append(w)
                elif not word.isspace():
                    value = value + word
                else:
                    await resolve(key, value, handle)
                    key = ""
                    value = ""
                    handle = _equal
            if key or value:
                await resolve(key, value, handle)

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
                raise checks.CustomError("Malformed URL.")
        else:
            raise checks.CustomError(f"This command accepts url with scheme {self._accept_string} only.")

#==================================================================================================================================================

def _transfer_modding(from_, to_):
    try:
        to_.category = from_.category
    except AttributeError:
        return
    else:
        to_.brief = from_.brief
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
