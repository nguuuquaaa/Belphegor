import discord
from discord.ext import commands
from .utils import checks
import math
import cmath
import operator
import re
import traceback
import asyncio
import random
import collections
import numpy

#==================================================================================================================================================

def combination(n, k):
    t = 1
    b = 1
    if n >= k >= 0:
        for i in range(min(n-k, k)):
            t *= n - i
            b *= i + 1
    else:
        return 0
    return t // b

#==================================================================================================================================================

class ParseError(Exception):
    pass

class CommonParseError(Exception):
    pass

#==================================================================================================================================================

class BaseParse:
    MAX_POWER_LOG = 300
    MAX_FACTORIAL = 50

    SIGNS = {
        "+":    1,
        "-":    -1
    }
    OPS = {
        "*":    operator.mul,
        "/":    operator.truediv,
        "//":   operator.floordiv,
        "%":    operator.mod
    }
    FUNCS = {
        "sin":      cmath.sin,
        "cos":      cmath.cos,
        "tan":      cmath.tan,
        "cot":      lambda x: cmath.cos(x)/cmath.sin(x),
        "arcsin":   math.asin,
        "arccos":   math.acos,
        "arctan":   math.atan,
        "log":      cmath.log10,
        "ln":       cmath.log,
        "sqrt":     cmath.sqrt,
        "abs":      abs
    }
    SPECIAL = {
        "^":    pow,
        "**":   pow,
        "!":    math.factorial,
        "C":    combination
    }
    CONSTS = {
        "e":    math.e,
        "π":    math.pi,
        "pi":   math.pi,
        "τ":    math.tau,
        "tau":  math.tau,
        "i":    1j,
        "inf":  float("inf"),
        "∞":    float("inf")
    }

    def DO_NOTHING(x):
        return x

    ENCLOSED = {
        None:       (None, DO_NOTHING),
        "(":        (")", DO_NOTHING),
        "[":        ("]", DO_NOTHING),
        "{":        ("}", DO_NOTHING),
        "\u2308":   ("\u2309", math.ceil),
        "\u230a":   ("\u230b", math.floor)
    }

    CLOSED = tuple(c[0] for c in ENCLOSED.values())

    BUILTINS = (OPS, FUNCS, SPECIAL, CONSTS)

    WHITESPACES = (
        "\u0009", "\u000a", "\u000b", "\u000c", "\u000d", "\u0020", "\u0085", "\u00a0", "\u1680", "\u2000", "\u2001", "\u2002", "\u2003",
        "\u2004", "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a", "\u200b", "\u2028", "\u2029", "\u202f", "\u205f", "\u3000"
    )

    def __init__(self):
        self.log_lines = []
        self.name_lens = []
        self.user_variables = {}
        self.user_functions = {}
        self.signals = [",", ";"]
        self.things_to_check = (*self.BUILTINS, self.user_functions, self.user_variables)

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
        self.name_lens.clear()
        for kind in self.things_to_check:
            for k in kind:
                l = len(k)
                if l not in self.name_lens:
                    self.name_lens.append(l)
        self.name_lens.sort(reverse=True)

    def set_base(self, base):
        self.base = base
        if base == 2:
            self.base_str = "bin: "
            self.strfmt = "b"
            self.max_power = self.MAX_POWER_LOG * math.log2(10)
            self.digits = ("0", "1")
        elif base == 8:
            self.base_str = "oct: "
            self.strfmt = "o"
            self.max_power = self.MAX_POWER_LOG * 3 * math.log2(10)
            self.digits = ("0", "1", "2", "3", "4", "5", "6", "7")
        elif base == 10:
            self.base_str = ""
            self.strfmt = "d"
            self.max_power = self.MAX_POWER_LOG
            self.digits = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
        elif base == 16:
            self.base_str = "hex: "
            self.strfmt = "x"
            self.max_power = self.MAX_POWER_LOG * 4 * math.log2(10)
            self.digits = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f")

    def peek_ahead(self, number=1):
        nx = self.current_index
        return self.text[nx:nx+number]

    def parse_number(self):
        get_it = []
        is_int = True
        while True:
            n = self.cur()
            if n == ".":
                if self.base == 10:
                    if is_int:
                        is_int = False
                        get_it.append(n)
                    else:
                        raise ParseError("Not a number.")
                else:
                    raise ParseError("Float is not allow in non-decimal mode.")
            elif n in self.digits:
                get_it.append(n)
            elif n in self.WHITESPACES:
                pass
            else:
                break
            self.next()
        n = "".join(get_it)
        if is_int:
            return int(n, self.base)
        else:
            return float(n)

    def parse_next(self):
        while self.cur() in self.WHITESPACES:
            self.next()
        n = self.cur()
        if n is None:
            self.current_parse = None
        else:
            for i in self.name_lens:
                fn = self.peek_ahead(i)
                for kind in self.things_to_check:
                    if fn in kind:
                        self.next(i)
                        self.current_parse = kind[fn]
                        break
                else:
                    continue
                break
            else:
                if n in self.digits or n == ".":
                    self.current_parse = self.parse_number()
                else:
                    self.current_parse = n
                    self.next()
        self.log_lines.append(f"parsed {type(self.current_parse)}: {self.current_parse}")
        return self.current_parse

    def parse_special(self, value):
        self.log_lines.append(f"start special at {self.current_parse}")
        c = self.current_parse
        if c == self.SPECIAL["!"]:
            self.parse_next()
            if isinstance(value, int):
                if value > self.MAX_FACTORIAL:
                    raise ParseError(f"Limit for factorial is {self.MAX_FACTORIAL}!")
                elif value < 0:
                    raise ParseError("Can't factorial negative number.")
                else:
                    result = c(value)
            else:
                raise ParseError("Can't factorial non-integer.")
        elif c == self.SPECIAL["^"]:
            n = self.parse_next()
            if n in self.ENCLOSED:
                p = self.parse_level()
            else:
                p = n
                self.parse_next()
            r = getattr(p, "real", p)
            v = getattr(value, "real", value)
            if v == 0 or v == self.CONSTS["inf"] or r == self.CONSTS["inf"] or r * math.log10(abs(v)) < self.max_power:
                result = c(value, p)
            else:
                raise ParseError(f"Limit for power in base {self.base} is 10^{self.max_power}")
        elif c == self.SPECIAL["C"]:
            n = self.parse_next()
            if n in self.ENCLOSED:
                k = self.parse_level()
            else:
                k = n
                self.parse_next()
            if isinstance(value, int) and isinstance(k, int):
                if value > 2 * self.MAX_FACTORIAL:
                    raise ParseError(f"Limit for combination is n <= {2*self.MAX_FACTORIAL}")
                else:
                    result = c(value, k)
            else:
                raise ParseError("Can't factorial non-integer.")
        else:
            result = None
        self.log_lines.append(f"end special at {self.current_parse}")
        return result

    def parse_level(self):
        self.log_lines.append(f"start level at {self.current_parse}")
        result = None
        sign = 1
        start = self.current_parse
        end, func = self.ENCLOSED[start]
        self.parse_next()
        while True:
            n = self.current_parse
            if n == end:
                break
            elif n in self.CLOSED and n != end:
                raise ParseError("No closing bracket.")
            elif n in self.SIGNS:
                if sign:
                    sign = sign * self.SIGNS[n]
                self.parse_next()
            else:
                r = sign * self.parse_group()
                if result is None:
                    result = r
                else:
                    result = result + r
                sign = 1

        result = func(result)
        self.parse_next()
        self.log_lines.append(f"end level at {self.current_parse}")
        return result

    def parse_group(self):
        self.log_lines.append(f"start group at {self.current_parse}")
        result = None
        last_op = None
        last_funcs = []
        n = True
        while True:
            n = self.current_parse
            if n in self.SIGNS or n in self.CLOSED or n in self.signals:
                if last_op or last_funcs:
                    raise CommonParseError
                break

            elif n in self.OPS.values():
                if last_op:
                    raise CommonParseError
                else:
                    last_op = n
                self.parse_next()
                continue

            elif n in self.FUNCS.values():
                last_funcs.append(n)
                self.parse_next()
                continue

            elif n in self.user_functions.values():
                args = self.parse_func_args()
                value = n(args)

            elif n in self.ENCLOSED:
                value = self.parse_level()

            else:
                value = n
                self.parse_next()

            while True:
                after = self.parse_special(value)
                if after is not None:
                    value = after
                else:
                    break

            if last_funcs:
                for f in reversed(last_funcs):
                    value = f(value)
                last_funcs.clear()

            if last_op:
                if result is not None:
                    result = last_op(result, value)
                    last_op = None
                else:
                    raise CommonParseError
            else:
                if result is not None:
                    result = self.OPS["*"](result, value)
                else:
                    result = value

        self.log_lines.append(f"end group at {self.current_parse}")
        return result

    def parse_func_args(self):
        self.log_lines.append(f"start func args at {self.current_parse}")
        start = self.parse_next()
        if start != "(":
            raise CommonParseError

        self.parse_next()
        result = []
        sign = 1
        cur = None

        while True:
            n = self.current_parse
            if n == ")":
                result.append(cur)
                break
            elif n in self.CLOSED and n != ")":
                raise ParseError("No closing bracket.")
            elif n in self.SIGNS:
                if sign:
                    sign = sign * self.SIGNS[n]
                self.parse_next()
            elif n in self.signals:
                result.append(cur)
                cur = None
                sign = 1
                self.parse_next()
            else:
                r = sign * self.parse_group()
                if cur is None:
                    cur = r
                else:
                    cur = cur + r
                sign = 1

        self.parse_next()
        self.log_lines.append(f"end func args at {self.current_parse}")
        return result

#==================================================================================================================================================

class MathFunction(BaseParse):
    def __init__(self, text, args, variables, functions, base):
        super().__init__()
        self.text = text.partition("\n")[0]
        self.args = collections.OrderedDict((k, None) for k in args)
        self.user_variables.update(variables)
        self.user_functions.update(functions)
        self.things_to_check = (*self.things_to_check, self.args)
        self.set_base(base)

    def __call__(self, args):
        if len(args) != len(self.args):
            raise ParseError("Number of arguments does not match.")
        for i, a in enumerate(self.args):
            self.args[a] = args[i]
        self.reset()
        result = self.parse_level()
        for a in self.args:
            self.args[a] = None
        return result

#==================================================================================================================================================

class MathParse(BaseParse):
    VAR_REGEX = re.compile(r"\s*(\w+)\s*")
    FUNC_REGEX = re.compile(r"\s*(\w+)\s*[,;]?\s*")

    BASE_TRANS = {
        "bin:": 2,
        "oct:": 8,
        "dec:": 10,
        "hex:": 16
    }

    def __init__(self, text):
        super().__init__()
        self.formulas = [t for t in text.splitlines() if t]
        if len(self.formulas) > 20:
            raise ParseError("Oi, don't do that many calculations in one go.")

    def how_to_display(self, number):
        if number == float("nan"):
            return number, "NotNumber"
        elif number == self.CONSTS["inf"]:
            return number, "∞"
        elif number == -self.CONSTS["inf"]:
            return number, "-∞"

        value = int(round(number))
        if cmath.isclose(value, number, rel_tol=1e-10, abs_tol=1e-10):
            s = f"{value:{self.strfmt}}"
        else:
            value = number
            s = f"{value:.10f}".rstrip("0").rstrip(".")
        return value, s

    def result(self):
        results = []
        for f in self.formulas:
            s = f[:4]
            if s in self.BASE_TRANS:
                self.set_base(self.BASE_TRANS[s])
                f = f[4:]
            else:
                self.set_base(10)
            stuff = f.partition("=")
            if stuff[1]:
                m = self.VAR_REGEX.fullmatch(stuff[0])
                if m:
                    var_name = m.group(1)
                    if var_name[0] in self.digits:
                        raise ParseError("Variable name should not start with digit.")

                    for kind in (self.FUNCS, self.CONSTS, self.SPECIAL, self.user_functions):
                        if var_name in kind:
                            raise ParseError(f"Name {var_name} is already taken.")
                    else:
                        self.text = stuff[2]
                else:
                    proc = stuff[0].partition("(")
                    raw_args = proc[2].rstrip(") \t")
                    args = self.FUNC_REGEX.findall(raw_args)
                    if args:
                        for a in args:
                            if a[0] in self.digits:
                                raise ParseError("Argument name should not start with digit.")

                            for kind in (self.FUNCS, self.CONSTS, self.SPECIAL, self.user_variables):
                                if a in kind:
                                    raise ParseError(f"Don't use {a} as argument, it's already taken.")
                        else:
                            func = MathFunction(stuff[2], args, variables=self.user_variables, functions=self.user_functions, base=self.base)
                            mf = self.VAR_REGEX.fullmatch(proc[0])
                            if mf:
                                func_name = mf.group(1)
                                if func_name[0] in self.digits:
                                    raise ParseError("Function name should not start with digit.")
                                for kind in (self.FUNCS, self.CONSTS, self.SPECIAL, self.user_variables):
                                    if func_name in kind:
                                        raise ParseError(f"Name {func_name} is already taken.")
                                self.user_functions[func_name] = func
                                da = ", ".join(args)
                                results.append(f"Registered {func_name}({da})")
                                continue
                            else:
                                raise ParseError("Your function name is bad and you should feel bad.")
                    else:
                        raise ParseError("Bad definition detected.")
            else:
                self.text = f

            self.reset()
            result = self.parse_level()
            if isinstance(result, complex):
                if self.base == 10:
                    r, rstr = self.how_to_display(result.real)
                    i, istr = self.how_to_display(result.imag)
                    if i == 0:
                        value = r
                        s = rstr
                    elif r == 0:
                        value = i * 1j
                        s = f"{istr}i"
                    else:
                        value = r + i * 1j
                        if i > 0:
                            s = f"{rstr} + {istr}i"
                        else:
                            s = f"{rstr} - {istr.lstrip('-')}i"
                else:
                    raise ParseError("Complex number is not allowed in non-decimal mode.")
            else:
                value, s = self.how_to_display(result)

            if stuff[1]:
                x = var_name
                self.user_variables[x] = value
                results.append(f"{self.base_str}{x} = {s}")
            else:
                results.append(f"{self.base_str}{s}")
        return results

    def log(self):
        return "\n".join(self.log_lines)

    def show_parse_error(self):
        end_index = self.current_index
        start_index = max(end_index - 50, 0)
        s = self.text[start_index:end_index]
        if len(s) < 50:
            r = f"{s}\u032d"
        else:
            r = f"...{s}\u032d"
        return r

#==================================================================================================================================================

class Calculator:
    def __init__(self, bot):
        self.bot = bot
        try:
            self.enable_log = bot.enable_calc_log
        except AttributeError:
            self.enable_log = False
        else:
            del bot.enable_calc_log

    def __unload(self):
        self.bot.enable_calc_log = self.enable_log

    @commands.command(aliases=["calc"])
    async def calculate(self, ctx, *, stuff):
        '''
            `>>calc <formulas>`
            Formulas are separated by linebreak. You can codeblock the whole thing for easier on the eyes.
            Acceptable expressions:
             - Operators `+` , `-` , `*` , `/` (true div), `//` (div mod), `%` (mod), `^` or `**` (pow), `!` (factorial)
             - Functions `sin`, `cos`, `tan`, `cot`, `log` (base 10), `ln` (natural log), `sqrt` (square root), `abs` (absolute value), `nCk` (combination)
             - Constants `e`, `pi`, `π`, `tau`, `τ`, `i` (imaginary), `inf` or `∞` (infinity, use at your own risk)
             - Enclosed `()`, `[]`, `{{}}`, `\u2308 \u2309` (ceil), `\u230a \u230b` (floor)
             - Set a variable to a value (value can be a calculable formula) for next calculations
             - Define a function. User functions must be in `func_name(arg1, arg2...)` format, both at defining and using.
        '''
        if stuff.startswith("```"):
            stuff = stuff.partition("\n")[2]
        stuff = stuff.strip("` \n")
        try:
            m = MathParse(stuff)
            results = await asyncio.wait_for(self.bot.loop.run_in_executor(None, m.result), 10)
        except ParseError as e:
            await ctx.send(e)
        except asyncio.TimeoutError:
            await ctx.send("Result too large.")
        except ZeroDivisionError:
            await ctx.send("Division by zero.")
        except ValueError:
            await ctx.send("Calculation error. Probably incomprehensible calculation involved ∞ or something.")
        except OverflowError:
            await ctx.send("Input number too big. U sure need this one?")
        except:
            await ctx.send(f"Parsing error.\n```\n{m.show_parse_error()}\n```")
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
            await ctx.deny()
        else:
            self.enable_log = True
            await ctx.confirm()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Calculator(bot))
