import discord
from discord.ext import commands
from .utils import checks
import math
import operator
import re
import traceback
import asyncio

#==================================================================================================================================================

class ParseError(Exception):
    pass

#==================================================================================================================================================

class MathParse:
    DIGITS = tuple(str(i) for i in range(10))
    SIGNS = {
        "+":    1,
        "-":    -1
    }
    OPS = {
        "*":    operator.mul,
        "/":    operator.truediv,
        "//":   operator.floordiv,
        "%":    operator.mod,

    }
    FUNCS = {
        "sin":  math.sin,
        "cos":  math.cos,
        "tan":  math.tan,
        "cot":  lambda x: 1/math.tan(x),
        "log":  math.log10,
        "ln":   math.log,
        "sqrt": math.sqrt
    }
    CONSTS = {
        "e":    math.e,
        "π":    math.pi,
        "pi":   math.pi,
        "τ":    math.tau,
        "tau":  math.tau
    }

    def DO_NOTHING(x):
        return x

    ENCLOSED = {
        "(":        (")", DO_NOTHING),
        "[":        ("]", DO_NOTHING),
        "{":        ("}", DO_NOTHING),
        "|":        ("|", abs),
        "\u2308":   ("\u2309", math.ceil),
        "\u230a":   ("\u230b", math.floor)
    }

    CLOSED = tuple(c[0] for c in ENCLOSED.values())

    def __init__(self, text):
        self.text = "".join((t for t in text if t not in " \t\n\r"))
        self.last_index = len(self.text) - 1
        self.current_index = 0
        self.current_parse = None

    def next(self, jump=1):
        self.current_index += jump

    def cur(self):
        ci = self.current_index
        if 0 <= ci <= self.last_index:
            return self.text[ci]
        else:
            return None

    def peek_ahead(self, number=1):
        nx = self.current_index
        return self.text[nx:nx+number]

    def parse_number(self):
        get_it = []
        output = int
        while True:
            n = self.cur()
            if n == ".":
                if output is int:
                    output = float
                    get_it.append(n)
                else:
                    raise ParseError("Not a number.")
            elif n in self.DIGITS:
                get_it.append(n)
            else:
                break
            self.next()
        return output("".join(get_it))

    def parse_next(self):
        n = self.cur()
        if n is None:
            self.current_parse = None
        elif n in self.DIGITS:
            self.current_parse = self.parse_number()
        elif n in self.OPS:
            if n == "/":
                if self.peek_ahead(2) == "//":
                    self.next(2)
                    self.current_parse = self.OPS["//"]
                else:
                    self.next()
                    self.current_parse = self.OPS["/"]
            else:
                self.next()
                self.current_parse = self.OPS[n]
        else:
            for i in range(1, 5):
                fn = self.peek_ahead(i)
                if fn in self.FUNCS:
                    self.next(i)
                    self.current_parse = self.FUNCS[fn]
                    break
                elif fn in self.CONSTS:
                    self.next(i)
                    self.current_parse = self.CONSTS[fn]
                    break
            else:
                self.next()
                self.current_parse = n
        return self.current_parse

    def parse_special(self, value):
        if self.current_parse == "!":
            self.parse_next()
            if value > 20:
                raise ParseError("Why you need this large number.")
            return math.factorial(value)
        elif self.current_parse == "^":
            n = self.parse_next()
            if n in self.ENCLOSED:
                e = self.ENCLOSED[n]
                p = e[1](self.parse_level(e[0]))
            else:
                p = n
                self.parse_next()
            if value == 0 or p * math.log10(value) < 300:
                return value ** p
            else:
                raise ParseError("Why you need this large number.")
        else:
            return None

    def parse_level(self, end=None):
        result = None
        n = 0
        sign = None
        self.parse_next()
        while True:
            n = self.current_parse

            if n == end:
                break
            elif n is None and end is not None:
                raise ParseError("No closing bracket.")
            elif n in self.SIGNS:
                if sign:
                    sign = sign * self.SIGNS[n]
                else:
                    sign = self.SIGNS[n]
                self.parse_next()
            elif n in self.ENCLOSED:
                e = self.ENCLOSED[n]
                if result is None:
                    result = e[1](self.parse_level(e[0]))
                else:
                    result = result + sign * e[1](self.parse_level(e[0]))
            else:
                if result is None:
                    if sign:
                        result = sign * self.parse_group()
                    else:
                        result = self.parse_group()
                else:
                    result = result + sign * self.parse_group()
                sign = None

        self.parse_next()
        return result

    def parse_group(self):
        result = None
        last_ops = None
        last_func = None
        n = True
        while True:
            n = self.current_parse
            if n in self.SIGNS or n is None or n in self.CLOSED:
                if last_ops:
                    raise ParseError("Oi, you put that operator there but didn't put any value after.")
                break

            if n in self.OPS.values():
                last_ops = n
                self.parse_next()
                continue
            elif n in self.FUNCS.values():
                last_func = n
                self.parse_next()
                continue
            elif n in self.ENCLOSED:
                e = self.ENCLOSED[n]
                value = e[1](self.parse_level(e[0]))
            else:
                value = n
                self.parse_next()

            while True:
                after = self.parse_special(value)
                if after:
                    value = after
                else:
                    break

            if last_func:
                value = last_func(value)
                last_func = None

            if last_ops:
                if result:
                    result = last_ops(result, value)
                    last_ops = None
                else:
                    raise ParseError("Oi, you put that operator there but didn't put any value before.")
            else:
                result = value

        return result

    def result(self):
        return self.parse_level()

#==================================================================================================================================================

class Calculator:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["calc"])
    async def calculate(self, ctx, *, stuff):
        '''
            `>>calc <formula>`
            Self-explanation.
            Acceptable expressions:
             - Operators `+` , `-` , `*` , `/` (true div), `//` (div mod), `%` (mod), `^` (pow), `!` (factorial)
             - Functions `sin`, `cos`, `tan`, `cot`, `log` (base 10), `ln` (natural log), `sqrt` (square root)
             - Constants `e`, `pi`, `π`, `tau`, `τ`
             - Enclosed `()`, `[]`, `{{}}`, `||` (abs), `\u2308 \u2309` (ceil), `\u230a \u230b` (floor)

        '''
        m = MathParse(stuff)
        try:
            r = await asyncio.wait_for(self.bot.loop.run_in_executor(None, m.result), 10)
        except ParseError as e:
            await ctx.send(e)
        except asyncio.TimeoutError:
            await ctx.send("Result too large.")
        except:
            tb = f"```\n{traceback.format_exc()}\n```"
            if hasattr(self.bot, "error_hook"):
                await ctx.send("Parsing error.")
                await self.bot.error_hook.execute(tb)
            else:
                print(tb)
        else:
            i = int(r)
            if i == r:
                await ctx.send(i)
            else:
                await ctx.send(f"{r:.5f}")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Calculator(bot))
