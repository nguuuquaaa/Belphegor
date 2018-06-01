import discord
from discord.ext import commands
from . import utils
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
import time
import functools

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

def greatest_common_factor(*args):
    if len(args) < 2:
        raise CommonParseError
    else:
        if not isinstance(args[0], int):
            raise ParseError("Can't calculate greatest common factor of non-integers.")

        result = abs(args[0])
        for i in range(1, len(args)):
            if not isinstance(args[i], int):
                raise ParseError("Can't calculate greatest common factor of non-integers.")
            b = abs(args[i])
            result = math.gcd(result, b)

        return result

def least_common_multiple(*args):
    if len(args) < 2:
        raise CommonParseError
    else:
        if not isinstance(args[0], int):
            raise ParseError("Can't calculate least common multiple of non-integers.")

        result = abs(args[0])
        for i in range(1, len(args)):
            if not isinstance(args[i], int):
                raise ParseError("Can't calculate least common multiple of non-integers.")
            b = abs(args[i])
            result = result * b // math.gcd(result, b)

        return result

def to_real_number(func):
    @functools.wraps(func)
    def do_func(*args):
        result = func(*args)
        if getattr(result, "imag", 0) == 0:
            result = getattr(result, "real", result)
        return result
    return do_func

#==================================================================================================================================================

class ParseError(Exception):
    pass

class CommonParseError(Exception):
    pass

#==================================================================================================================================================

class NoValue:
    def __init__(self, var):
        self.var = var

    def __repr__(self):
        return "NoValue"

    def __str__(self):
        return f"{self.var} = NoValue"

#==================================================================================================================================================

class Reduce:
    MAX_RANGE = 100

    def __init__(self, kind, func, from_, to_):
        if to_ > from_:
            self.delta = 1
        else:
            self.delta = -1
        if abs(to_ - from_) > self.MAX_RANGE:
            raise ParseError(f"Sigma max range is {self.MAX_RANGE}.")
        if func.reduce:
            raise ParseError("Nested reduce/sigma is not accepted.")
        self.kind = kind
        self.func = func
        self.from_ = from_
        self.to_ = to_

    def __call__(self):
        result = functools.reduce(self.kind, (self.func(k) for k in range(self.from_, self.to_+self.delta, self.delta)))
        return result

class Sigma(Reduce):
    MAX_RANGE = 1000

#==================================================================================================================================================

class BaseParse:
    MAX_POWER_LOG = 300
    MAX_FACTORIAL = 100

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
        "sin":      to_real_number(cmath.sin),
        "cos":      to_real_number(cmath.cos),
        "tan":      to_real_number(cmath.tan),
        "cot":      to_real_number(lambda x: cmath.cos(x)/cmath.sin(x)),
        "asin":     to_real_number(cmath.asin),
        "arcsin":   to_real_number(cmath.asin),
        "acos":     to_real_number(cmath.acos),
        "arccos":   to_real_number(cmath.acos),
        "atan":     to_real_number(cmath.atan),
        "arctan":   to_real_number(cmath.atan),
        "log":      to_real_number(cmath.log10),
        "ln":       to_real_number(cmath.log),
        "sqrt":     to_real_number(cmath.sqrt),
        "abs":      abs,
        "sign":     numpy.sign,
        "sgn":      numpy.sign,
        "gcd":      greatest_common_factor,
        "gcf":      greatest_common_factor,
        "lcm":      least_common_multiple,
        "max":      max,
        "min":      min
    }
    SPECIAL_OPS = {
        "^":    pow,
        "**":   pow,
        "!":    math.factorial,
        "C":    combination,
        "°":    math.radians
    }
    SPECIAL_FUNCS = {
        "sigma":    Sigma,
        "Σ":        Sigma,
        "reduce":   Reduce
    }
    CONSTS = {
        "e":    math.e,
        "π":    math.pi,
        "pi":   math.pi,
        "τ":    math.tau,
        "tau":  math.tau,
        "i":    1j,
        "inf":  float("inf"),
        "∞":    float("inf"),
        "None": NoValue(None)
    }

    def do_nothing(x):
        return x

    ENCLOSED = {
        None:       (None, do_nothing),
        "(":        (")", do_nothing),
        "[":        ("]", do_nothing),
        "{":        ("}", do_nothing),
        "\u2308":   ("\u2309", math.ceil),
        "\u230a":   ("\u230b", math.floor)
    }

    CLOSED = tuple(c[0] for c in ENCLOSED.values())

    SIGNALS = (",", ";")

    BUILTINS = (OPS, FUNCS, SPECIAL_OPS, SPECIAL_FUNCS, CONSTS)

    WHITESPACES = (
        "\u0009", "\u000a", "\u000b", "\u000c", "\u000d", "\u0020", "\u0085", "\u00a0", "\u1680", "\u2000", "\u2001", "\u2002", "\u2003",
        "\u2004", "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a", "\u200b", "\u2028", "\u2029", "\u202f", "\u205f", "\u3000"
    )

    def __init__(self):
        self.log_lines = []
        self.name_lens = []
        self.user_variables = {}
        self.user_functions = {}
        self.things_to_check = (*self.BUILTINS, self.user_functions, self.user_variables)

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
            self.max_power = self.MAX_POWER_LOG * math.log10(2)
            self.digits = ("0", "1")
        elif base == 8:
            self.base_str = "oct: "
            self.strfmt = "o"
            self.max_power = self.MAX_POWER_LOG * math.log10(8)
            self.digits = ("0", "1", "2", "3", "4", "5", "6", "7")
        elif base == 10:
            self.base_str = ""
            self.strfmt = "d"
            self.max_power = self.MAX_POWER_LOG
            self.digits = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9")
        elif base == 16:
            self.base_str = "hex: "
            self.strfmt = "x"
            self.max_power = self.MAX_POWER_LOG * math.log10(16)
            self.digits = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f")

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

    def log_this(kind):
        def wrap(func):
            def f(self, *args, **kwargs):
                self.log_lines.append(f"start {kind} at {self.current_parse}")
                try:
                    ret = func(self, *args, **kwargs)
                except Exception as e:
                    if not hasattr(e, "target"):
                        e.target = self
                    raise e
                self.log_lines.append(f"end {kind} at {self.current_parse}")
                return ret
            return f
        return wrap

    @log_this("next value")
    def parse_next_value(self):
        n = self.current_parse
        if n in self.FUNCS.values():
            result = self.parse_function()
        elif n in self.user_functions.values():
            self.parse_next()
            args = self.parse_func_args()
            result = n(*args)
        elif n in self.SPECIAL_FUNCS.values():
            result = self.parse_reduce(n)
        elif n in self.ENCLOSED:
            result = self.parse_level()
        else:
            result = n
            self.parse_next()
        result = self.parse_special(result)
        return result

    @log_this("special")
    def parse_special(self, value):
        c = self.current_parse
        if c == self.SPECIAL_OPS["!"]:
            if isinstance(value, int):
                if value > self.MAX_FACTORIAL:
                    raise ParseError(f"Limit for factorial is {self.MAX_FACTORIAL}!")
                elif value < 0:
                    raise ParseError("Can't factorial negative number.")
                else:
                    result = c(value)
            else:
                raise ParseError("Can't factorial non-integer.")
            self.parse_next()
            result = self.parse_special(result)
        elif c == self.SPECIAL_OPS["^"]:
            self.parse_next()
            p = self.parse_next_value()
            r = getattr(p, "real", p)
            v = getattr(value, "real", value)
            if v == 0 or v == self.CONSTS["inf"] or r == self.CONSTS["inf"] or r * math.log10(abs(v)) < self.max_power:
                result = c(value, p)
            else:
                raise ParseError(f"Limit for power in base {self.base} is 10^{int(self.max_power)}")
        elif c == self.SPECIAL_OPS["C"]:
            self.parse_next()
            k = self.parse_next_value()
            if isinstance(value, int) and isinstance(k, int):
                if value > 2 * self.MAX_FACTORIAL:
                    raise ParseError(f"Limit for combination is n <= {2*self.MAX_FACTORIAL}")
                else:
                    result = c(value, k)
            else:
                raise ParseError("Can't combination non-integer.")
        elif c == self.SPECIAL_OPS["°"]:
            if isinstance(value, complex):
                raise ParseError("Degree can't be complex number.")
            else:
                result = c(value)
            self.parse_next()
            result = self.parse_special(result)
        else:
            result = value
        return result

    @log_this("level")
    def parse_level(self):
        result = None
        sign = 1
        start = self.current_parse
        end, func = self.ENCLOSED[start]
        self.parse_next()
        while True:
            n = self.current_parse
            if n == end:
                break
            elif n in self.CLOSED:
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
        return result

    @log_this("group")
    def parse_group(self):
        result = None
        last_op = None
        n = True
        while True:
            n = self.current_parse
            if n in self.SIGNS or n in self.CLOSED or n in self.SIGNALS:
                if last_op:
                    raise CommonParseError
                break

            elif n in self.OPS.values():
                if last_op:
                    raise CommonParseError
                else:
                    last_op = n
                self.parse_next()
                continue

            else:
                value = self.parse_next_value()

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

        return result

    @log_this("function")
    def parse_function(self):
        f = self.current_parse
        n = self.parse_next()
        if n in self.ENCLOSED:
            args = self.parse_func_args()
            result = f(*args)
        else:
            value = self.parse_next_value()
            result = f(value)
        return result

    @log_this("func args")
    def parse_func_args(self):
        start = self.current_parse
        if start != "(":
            raise CommonParseError

        self.parse_next()
        result = []
        sign = 1
        cur = None

        while True:
            n = self.current_parse
            if n == ")":
                if cur is None:
                    if len(result) > 0:
                        raise CommonParseError
                else:
                    result.append(cur)
                break
            elif n in self.CLOSED:
                raise ParseError("No closing bracket.")
            elif n in self.SIGNS:
                if sign:
                    sign = sign * self.SIGNS[n]
                self.parse_next()
            elif n in self.SIGNALS:
                if cur is None:
                    raise CommonParseError
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
        return result

    @log_this("reduce")
    def parse_reduce(self, type=Sigma):
        n = self.parse_next()
        if n != "(":
            raise CommonParseError

        if type is Reduce:
            kind = self.parse_next()
            if kind not in self.FUNCS.values() and kind not in self.user_functions.values():
                raise CommonParseError
            n = self.parse_next()
            if n not in self.SIGNALS:
                raise CommonParseError
        elif type is Sigma:
            kind = operator.add

        var = self.parse_next()
        if not isinstance(var, NoValue):
            raise CommonParseError

        n = self.parse_next()
        if n not in self.SIGNALS:
            raise CommonParseError

        self.parse_next()
        from_to = []
        sign = 1
        cur = None

        while True:
            n = self.current_parse
            if n == ")":
                from_to.append(cur)
                break
            elif n in self.CLOSED:
                raise ParseError("No closing bracket.")
            elif n in self.SIGNS:
                if sign:
                    sign = sign * self.SIGNS[n]
                self.parse_next()
            elif n in self.SIGNALS:
                from_to.append(cur)
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

        if self.current_parse != ")" or len(from_to) != 2:
            raise CommonParseError

        n = self.parse_next()
        if n != "(":
            raise CommonParseError

        parens = 1
        start_index = self.current_index
        while True:
            n = self.parse_next()
            if n is None:
                raise ParseError("No closing bracket.")
            elif n == "(":
                parens += 1
                continue
            elif n == ")":
                parens -= 1
                if parens == 0:
                    end_index = self.current_index
                    break
            else:
                continue

        func_text = self.text[start_index:end_index-1]
        func = MathFunction(func_text, (var.var,), variables=self.user_variables, functions=self.user_functions, base=self.base)
        reduce = type(kind, func, from_to[0], from_to[1])
        self.parse_next()

        return reduce()

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

class MathFunction(BaseParse):
    def __init__(self, text, args, *, variables, functions, base):
        if not text:
            raise CommonParseError
        super().__init__()
        self.user_variables.update(variables)
        self.user_variables.update({k: NoValue(k) for k in args})
        self.user_functions.update(functions)
        self.set_base(base)
        self.text = text.partition("\n")[0].strip()
        self.args = args

        self.reduce = False
        self.tokens = []
        self.reset()
        while True:
            n = self.parse_next()
            if n is None:
                break
            else:
                if n in self.SPECIAL_FUNCS.values():
                    self.reduce = True
                self.tokens.append((n, self.current_index))
        self.parse_next = self.next_token

    def next_token(self):
        try:
            n = next(self.token_iter)
        except StopIteration:
            self.current_parse = None
        else:
            self.current_index = n[1]
            v = n[0]
            if isinstance(v, NoValue):
                self.current_parse = self.user_variables.get(v.var, v)
            else:
                self.current_parse = v
        finally:
            return self.current_parse

    def __call__(self, *args):
        if len(args) != len(self.args):
            raise ParseError("Number of arguments does not match.")
        for i, a in enumerate(self.args):
            self.user_variables[a] = args[i]

        self.current_parse = None
        self.token_iter = iter(self.tokens)
        result = self.parse_level()
        return result

    def __repr__(self):
        return "MathFunction"

    def __str__(self):
        return f"MathFunction({self.text})"

#==================================================================================================================================================

class MathParse(BaseParse):
    NAME_REGEX = re.compile(r"\s*(\w+)\s*")
    DLMT_REGEX = re.compile("|".join((re.escape(s) for s in BaseParse.SIGNALS)))

    BASE_TRANS = {
        "bin:": 2,
        "oct:": 8,
        "dec:": 10,
        "hex:": 16
    }

    MAX_VALUE = 10 ** 300

    def __init__(self, text):
        super().__init__()
        self.formulas = [t.strip() for t in text.splitlines()]
        if len(self.formulas) > 20:
            raise ParseError("Oi, don't do that many calculations in one go.")

    def how_to_display(self, number):
        if number == float("nan"):
            return number, "Not a number"
        elif number == self.CONSTS["inf"]:
            return number, "+∞"
        elif number == -self.CONSTS["inf"]:
            return number, "-∞"

        if number > self.MAX_VALUE:
            raise OverflowError
        value = int(round(number))
        if abs(number - value) < 1e-10:
            s = f"{value:{self.strfmt}}"
        else:
            value = number
            s = f"{value:.10f}".rstrip("0").rstrip(".")
        return value, s

    def result(self):
        results = []
        for f in self.formulas:
            if not f:
                results.append(f)
                continue
            s = f[:4]
            if s in self.BASE_TRANS:
                self.set_base(self.BASE_TRANS[s])
                f = f[4:]
            else:
                self.set_base(10)
            stuff = f.rpartition("=")
            if stuff[1]:
                m = self.NAME_REGEX.match(stuff[0])
                if m:
                    var_name = m.group(1)
                    if var_name[0] in self.digits:
                        raise ParseError("Name should not start with digit.")

                    for kind in (*self.BUILTINS, self.user_functions):
                        if var_name in kind:
                            raise ParseError(f"Name {var_name} is already taken.")

                    the_rest = stuff[0][len(m.group(0)):].strip()
                    if not the_rest:

                        #variable definition
                        self.text = stuff[2]
                        if self.text.strip() == "None":
                            x = var_name
                            self.user_variables[x] = NoValue(x)
                            results.append(f"Defined {x}")
                            continue
                        else:
                            pass
                    elif the_rest[0] == "(" and the_rest[-1] == ")":

                        #function definition
                        raw_text = the_rest[1:-1].strip()
                        args = []
                        if raw_text:
                            raw_args = self.DLMT_REGEX.split(raw_text)
                            for ra in raw_args:
                                ma = self.NAME_REGEX.fullmatch(ra)
                                if not ma:
                                    raise ParseError(f"Argument name \"{utils.discord_escape(ra.strip())}\" is not accepted.")
                                else:
                                    a = ma.group(1)
                                    if a[0] in self.digits:
                                        raise ParseError(f"Argument name should not start with digit.")
                                    for kind in (*self.BUILTINS, self.user_variables):
                                        if a in kind:
                                            raise ParseError(f"Don't use \"{utils.discord_escape(a)}\" as argument, it's already taken.")
                                    args.append(a)

                        func = MathFunction(stuff[2], args, variables=self.user_variables, functions=self.user_functions, base=self.base)
                        self.user_functions[var_name] = func
                        da = ", ".join(args)
                        results.append(f"Defined {var_name}({da})")
                        continue
                    else:
                        raise ParseError("Don't put strange symbol in var/func definition.")

                else:
                    raise ParseError(f"Bad definition detected.")
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
                        if i == 1:
                            istr = ""
                        elif i == -1:
                            istr = "-"
                        s = f"{istr}i"
                    else:
                        value = r + i * 1j
                        if i == 1 or i == -1:
                            istr = ""
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

            **Acceptable expressions:**
             - Operators `+` , `-` , `*` , `/` (true div), `//` (div mod), `%` (mod), `^`|`**` (pow), `!` (factorial)
             - Functions `sin`, `cos`, `tan`, `cot`, `arcsin`|`asin`, `arccos`|`acos`, `arctan`|`atan`, `log` (base 10), `ln` (natural log), `sqrt` (square root), `abs` (absolute value), `nCk` (combination), `sign`|`sgn` (sign function), `gcd`|`gcf` (greatest common divisor/factor), `lcm` (least common multiple), `max`, `min`
             - Constants `e`, `pi`|`π`, `tau`|`τ`, `i` (imaginary), `inf`|`∞` (infinity, use at your own risk)
             - Enclosed `()`, `[]`, `{{}}`, `\u2308 \u2309` (ceil), `\u230a \u230b` (floor)
             - Binary/octal/hexadecimal mode. Put `bin:`, `oct:`, `hex:` at the start to use that mode in current line. Default to decimal (`dec:`) mode (well of course)


             - Set a variable to a value (value can be a calculable formula) for next calculations
             - Define a function. User functions must be in `func_name(arg1, arg2...)` format, both at defining and using
             - Special function `sigma`|`Σ` (sum)
                Format: `sigma(counter, from, to)(formula)`
                Due to how parser works, counter must be a wildcard defined by `counter = None` prior to the sigma function.
             - Special function `reduce` (cumulate)
                Format: `reduce(function, counter, from, to)(formula)`
                It's like sigma, but use `function` instead of sum.
                `function` can be either builtin or user-defined, but must take exactly 2 arguments.
        '''
        stuff = utils.clean_codeblock(stuff)
        l = ""
        try:
            start = time.perf_counter()
            m = MathParse(stuff)
            results = await self.bot.loop.run_in_executor(None, m.result)
            end = time.perf_counter()
        except ParseError as e:
            await ctx.send(e)
        except ZeroDivisionError:
            await ctx.send("Division by zero.")
        except ValueError:
            await ctx.send("Calculation error. Probably incomprehensible calculation involved ∞ or something.")
        except OverflowError:
            await ctx.send("IO number too big. U sure need this one?")
        except Exception as e:
            target = getattr(e, "target", m)
            await ctx.send(f"Parsing error.\n```\n{target.show_parse_error()}\n```")
            l = traceback.format_exc()
        else:
            r = "\n".join(results)
            await ctx.send(f"Result in {1000*(end-start):.2f}ms\n```\n{r}\n```")
        finally:
            if self.enable_log:
                l = f"{m.log()}\n{l}"
                try:
                    await self.bot.error_hook.execute(l)
                except AttributeError:
                    print(l)

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
