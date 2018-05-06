import discord
from discord.ext import commands
from .utils import checks
import math
import operator
import re
import traceback
import asyncio

#==================================================================================================================================================

assign_regex = re.compile("\s*(\w+)[ \t]*\=\s*(.+)")

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

    BUILTIN_NAME_LENS = (4, 3, 2, 1)

    def __init__(self, text):
        self.formulas = text.splitlines()
        self.log_lines = []
        self.variables = {}

    def next(self, jump=1):
        self.current_index += jump

    def cur(self):
        ci = self.current_index
        if 0 <= ci <= self.last_index:
            return self.text[ci]
        else:
            return None

    def reset(self):
        self.last_index = len(self.text) - 1
        self.current_index = 0
        self.current_parse = None
        self.name_lens = list(self.BUILTIN_NAME_LENS)
        if self.variables:
            for k in self.variables:
                l = len(k)
                if l not in self.name_lens:
                    self.name_lens.append(l)
            self.name_lens.sort(reverse=True)

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
        while self.cur() in (" ", "\t"):
            self.next()
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
            for i in self.name_lens:
                fn = self.peek_ahead(i)
                if fn in self.FUNCS:
                    self.next(i)
                    self.current_parse = self.FUNCS[fn]
                    break
                elif fn in self.CONSTS:
                    self.next(i)
                    self.current_parse = self.CONSTS[fn]
                    break
                elif fn in self.variables:
                    self.next(i)
                    self.current_parse = self.variables[fn]
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
            if value == 0 or p * math.log10(abs(value)) < 300:
                return value ** p
            else:
                raise ParseError("Why you need this large number.")
        else:
            return None

    def parse_level(self, end=None):
        self.log_lines.append(f"start level at {self.current_parse}")
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
        self.log_lines.append(f"end level at {self.current_parse}")
        return result

    def parse_group(self):
        self.log_lines.append(f"start group at {self.current_parse}")
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
                if result:
                    result = self.OPS["*"](result, value)
                else:
                    result = value

        self.log_lines.append(f"end group at {self.current_parse}")
        return result

    def result(self):
        results = []
        for f in self.formulas:
            m = assign_regex.match(f)
            if m:
                for d in m.group(1):
                    if d not in self.DIGITS:
                        break
                else:
                    raise ParseError("WTF variable name...")
                self.text = m.group(2)
            else:
                self.text = f

            self.reset()
            r = self.parse_level()
            i = int(r)
            if i == r:
                s = str(i)
            else:
                i = r
                s = f"{r:.10f}".rstrip("0")

            if m:
                x = m.group(1)
                self.variables[x] = i
                results.append(f"{x} = {s}")
            else:
                results.append(s)
        return results

    def log(self):
        return "\n".join(self.log_lines)

#==================================================================================================================================================

class Calculator:
    def __init__(self, bot):
        self.bot = bot
        self.enable_log = False

    @commands.command(aliases=["calc"])
    async def calculate(self, ctx, *, stuff):
        '''
            `>>calc <formulas>`
            Formulas are separated by linebreak. You can codeblock the whole thing for easier on the eyes.
            Acceptable expressions:
             - Operators `+` , `-` , `*` , `/` (true div), `//` (div mod), `%` (mod), `^` (pow), `!` (factorial)
             - Functions `sin`, `cos`, `tan`, `cot`, `log` (base 10), `ln` (natural log), `sqrt` (square root)
             - Constants `e`, `pi`, `π`, `tau`, `τ`
             - Enclosed `()`, `[]`, `{{}}`, `||` (abs), `\u2308 \u2309` (ceil), `\u230a \u230b` (floor)
             - Set a variable to a value (value can be calculable formula) for next calculations
        '''
        if stuff.startswith("```"):
            stuff = stuff.partition("\n")[2]
        stuff = stuff.strip("` \n")
        m = MathParse(stuff)
        try:
            results = await asyncio.wait_for(self.bot.loop.run_in_executor(None, m.result), 10)
        except ParseError as e:
            await ctx.send(e)
        except asyncio.TimeoutError:
            await ctx.send("Result too large.")
        except:
            await ctx.send("Parsing error.")
            if self.enable_log:
                l = f"{m.log()}\n{traceback.format_exc()}"
                try:
                    await self.bot.error_hook.execute(l)
                except AttributeError:
                    print(l)
        else:
            r = "\n".join(results)
            await ctx.send(f"```\n{r}\n```")

    @commands.command(name="logcalc", aliases=["calclog"], hidden=True)
    @checks.owner_only()
    async def calc_log(self, ctx):
        if self.enable_log:
            self.enable_log = False
        else:
            self.enable_log = True
        await ctx.confirm()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Calculator(bot))
