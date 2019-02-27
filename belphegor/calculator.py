import discord
from discord.ext import commands
from . import utils
from .utils import checks, data_type, modding
import operator
import re
import traceback
import asyncio
import random
import time
import functools
import sympy
from datetime import datetime, timedelta
import collections

#==================================================================================================================================================

PRECISION = 100
EPSILON = sympy.Float(f"1e-{PRECISION-5}", PRECISION)
AFTER_DOT = 20
INF = sympy.oo
NAN = sympy.nan
ZINF = sympy.zoo
SPECIAL_NUMBERS = (INF, -INF, NAN, ZINF)

#==================================================================================================================================================

#I hate this, but sympy is pretty dumb for raising TypeError instead of return False for NaN comparison
def always_false(self, other):
    return False

cls = NAN.__class__

cls.__eq__ = always_false
cls.__ne__ = always_false
cls.__gt__ = always_false
cls.__ge__ = always_false
cls.__lt__ = always_false
cls.__le__ = always_false
#end haxing

#==================================================================================================================================================

def maybe_int(number):
    ret = []
    for n in (sympy.re(number), sympy.im(number)):
        if n in SPECIAL_NUMBERS:
            r = n
        else:
            nearest = n.round()
            if sympy.Abs(n - nearest) < EPSILON:
                r = sympy.Integer(nearest)
            else:
                r = n
        ret.append(r)
    return ret[0] + ret[1] * sympy.I

def greatest_common_factor(*args):
    if len(args) < 2:
        raise CommonParseError
    else:
        result = args[0]
        for i in args[1:]:
            result = result.gcd(i)

        return result

def least_common_multiple(*args):
    if len(args) < 2:
        raise CommonParseError
    else:
        result = args[0]
        for i in args[1:]:
            result = result.lcm(i)

        return result

def cube_root(number):
    return sympy.real_root(number, 3)

def nth_rooth(number, degree):
    return sympy.real_root(number, degree)

def log10(number):
    return sympy.log(number, 10)

def radians(deg):
    if sympy.im(deg) == 0:
        return deg * sympy.pi / 180
    else:
        raise CommonParseError

def round_float(number):
    return number.round()

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
        return self.var

#==================================================================================================================================================

class Reduce:
    MAX_RANGE = 100

    def __init__(self, kind, func, from_, to_):
        if to_ > from_:
            self.delta = 1
        else:
            self.delta = -1
        if sympy.Abs(to_ - from_) > self.MAX_RANGE:
            raise ParseError(f"{self.__class__.__name__} max range is {self.MAX_RANGE}.")
        if func.reduce:
            raise ParseError("Nested reduce/sigma is not accepted.")
        if isinstance(from_, sympy.Integer) and isinstance(to_, sympy.Integer):
            pass
        else:
            raise ParseError("From/to must be integers.")
        self.kind = kind
        self.func = func
        self.from_ = from_
        self.to_ = to_

    def __call__(self):
        return functools.reduce(self.kind, (self.func(k) for k in range(self.from_, self.to_+self.delta, self.delta)))

class Sigma(Reduce):
    MAX_RANGE = 1000

    def __call__(self):
        return sum(self.func(k) for k in range(self.from_, self.to_+self.delta, self.delta))

#==================================================================================================================================================

class BaseParse:
    MAX_POWER_LOG = 300
    MAX_FACTORIAL = 100

    SIGNS = {
        "+":    1,
        "-":    -1
    }
    OPS = {
        "*":        operator.mul,
        "/":        operator.truediv,
        "//":       operator.floordiv,
        "%":        operator.mod
    }
    FUNCS = {
        "sin":      sympy.sin,
        "cos":      sympy.cos,
        "tan":      sympy.tan,
        "cot":      sympy.cot,
        "asin":     sympy.asin,
        "arcsin":   sympy.asin,
        "acos":     sympy.acos,
        "arccos":   sympy.acos,
        "atan":     sympy.atan,
        "arctan":   sympy.atan,
        "acot":     sympy.acot,
        "arccot":   sympy.acot,
        "log":      log10,
        "ln":       sympy.log,
        "sqrt":     sympy.sqrt,
        "cbrt":     cube_root,
        "root":     sympy.real_root,
        "abs":      sympy.Abs,
        "sign":     sympy.sign,
        "sgn":      sympy.sign,
        "gcd":      greatest_common_factor,
        "gcf":      greatest_common_factor,
        "lcm":      least_common_multiple,
        "max":      max,
        "min":      min,
        "conj":     sympy.conjugate,
        "gamma":    sympy.gamma,
        "floor":    sympy.floor,
        "ceil":     sympy.ceiling,
        "round":    round_float
    }
    SPECIAL_OPS = {
        "^":        pow,
        "**":       pow,
        "!":        sympy.factorial,
        "C":        sympy.binomial,
        "°":        radians,
        "deg":      radians
    }
    SPECIAL_FUNCS = {
        "sigma":    Sigma,
        "Σ":        Sigma,
        "reduce":   Reduce
    }
    CONSTS = {
        "e":        sympy.E,
        "π":        sympy.pi,
        "pi":       sympy.pi,
        "τ":        sympy.pi * 2,
        "tau":      sympy.pi * 2,
        "i":        sympy.I,
        "inf":      sympy.oo,
        "∞":        sympy.oo,
        "counter":  NoValue(None)
    }

    def do_nothing(x):
        return x

    ENCLOSED = {
        None:       (None, do_nothing),
        "(":        (")", do_nothing),
        "[":        ("]", do_nothing),
        "{":        ("}", do_nothing),
        "\u2308":   ("\u2309", sympy.ceiling),
        "\u230a":   ("\u230b", sympy.floor)
    }

    CLOSED = tuple(c[0] for c in ENCLOSED.values())

    SIGNALS = (",", ";")

    BUILTINS = (OPS, FUNCS, SPECIAL_OPS, SPECIAL_FUNCS, CONSTS)

    WHITESPACES = (
        "\u0009", "\u000a", "\u000b", "\u000c", "\u000d", "\u0020", "\u0085", "\u00a0", "\u1680", "\u2000", "\u2001", "\u2002", "\u2003",
        "\u2004", "\u2005", "\u2006", "\u2007", "\u2008", "\u2009", "\u200a", "\u200b", "\u2028", "\u2029", "\u202f", "\u205f", "\u3000"
    )

    BASE_DIGITS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f")

    def __init__(self):
        self.log_lines = []
        self.name_lens = []
        self.user_variables = {}
        self.user_functions = {}
        self.things_to_check = (*self.BUILTINS, self.user_functions, self.user_variables)
        self.current_index = 0

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
            self.max_power = self.MAX_POWER_LOG * log10(2)
            self.digits = self.BASE_DIGITS[:base]
        elif base == 8:
            self.base_str = "oct: "
            self.strfmt = "o"
            self.max_power = self.MAX_POWER_LOG * log10(8)
            self.digits = self.BASE_DIGITS[:base]
        elif base == 10:
            self.base_str = ""
            self.strfmt = "d"
            self.max_power = self.MAX_POWER_LOG
            self.digits = self.BASE_DIGITS[:base]
        elif base == 16:
            self.base_str = "hex: "
            self.strfmt = "x"
            self.max_power = self.MAX_POWER_LOG * log10(16)
            self.digits = self.BASE_DIGITS[:base]

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
            return sympy.Integer(int(n, self.base))
        else:
            return maybe_int(sympy.Float(n, PRECISION))

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
        def wrapped(func):
            @functools.wraps(func)
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
        return wrapped

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
        elif n in self.SIGNS:
            self.parse_next()
            result = self.SIGNS[n] * self.parse_next_value()
        else:
            result = n
            self.parse_next()
        result = self.parse_special(result)
        return result

    @log_this("special")
    def parse_special(self, value):
        c = self.current_parse
        if c == self.SPECIAL_OPS["!"]:
            if value in SPECIAL_NUMBERS:
                result = c(value)
            elif value > self.MAX_FACTORIAL:
                raise ParseError(f"Limit for factorial is {self.MAX_FACTORIAL}!")
            elif value < 0:
                raise ParseError("Can't factorial negetive number.")
            elif sympy.Integer(value) == value:
                result = c(value)
            else:
                raise ParseError("Can't factorial non-integer.")
            self.parse_next()
            result = self.parse_special(result)
        elif c == self.SPECIAL_OPS["^"]:
            self.parse_next()
            p = self.parse_next_value()
            r = sympy.re(p)
            v = sympy.re(value)
            if v == 0 or v in SPECIAL_NUMBERS or r in SPECIAL_NUMBERS or r * log10(sympy.Abs(value)) < self.max_power:
                result = c(value, p)
            else:
                raise ParseError(f"Limit for power in base {self.base} is 10^{sympy.Integer(self.max_power)}")
        elif c == self.SPECIAL_OPS["C"]:
            self.parse_next()
            k = self.parse_next_value()
            if value in SPECIAL_NUMBERS:
                result = c(value, k)
            elif value > 2 * self.MAX_FACTORIAL:
                raise ParseError(f"Limit for combination is n <= {2*self.MAX_FACTORIAL}")
            else:
                result = c(value, k)
        elif c == self.SPECIAL_OPS["°"]:
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
                    result.append(maybe_int(cur))
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
                result.append(maybe_int(cur))
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
        if len(self.formulas) > 30:
            raise ParseError("Oi, don't do that many calculations in one go.")

        self.text = self.formulas[0]

    def how_to_display(self, number):
        if number > self.MAX_VALUE:
            raise OverflowError

        if isinstance(number, sympy.Integer):
            return f"{int(number):{self.strfmt}}"
        else:
            return f"{number.evalf(PRECISION):.{AFTER_DOT}f}".rstrip("0").rstrip(".")

    def result(self):
        results = []
        for f in self.formulas:
            if not f or f[0] == "#":
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

                    for kind in self.BUILTINS:
                        if var_name in kind:
                            raise ParseError(f"Name {var_name} is already taken.")

                    for kind in (self.user_functions, self.user_variables):
                        if var_name in kind:
                            kind.pop(var_name)

                    the_rest = stuff[0][len(m.group(0)):].strip()
                    if not the_rest:

                        #variable definition
                        self.text = stuff[2]
                        if self.text.strip() == "counter":
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
                                    for kind in self.BUILTINS:
                                        if a in kind:
                                            raise ParseError(f"Don't use \"{utils.discord_escape(a)}\" as argument, it's already taken.")
                                    args.append(a)

                        func = MathFunction(stuff[2], args, variables=self.user_variables, functions=self.user_functions, base=self.base)
                        self.user_functions[var_name] = func
                        da = ", ".join(args)
                        results.append(f"Defined {var_name}({da})")
                        continue
                    else:
                        raise ParseError("Bad definition detected.")

                else:
                    raise ParseError(f"Bad definition detected.")
            else:
                self.text = f

            self.reset()
            raw_result = self.parse_level()
            if raw_result in SPECIAL_NUMBERS:
                result = raw_result
                if result is NAN:
                    s = "NaN"
                elif result is INF:
                    s = "+∞"
                elif result is -INF:
                    s = "-∞"
                elif result is ZINF:
                    s = "z∞"
            else:
                result = maybe_int(raw_result)
                if self.base != 10 and result != raw_result:
                    raise ParseError("Non-integer is not allowed in non-decimal mode.")
                real = sympy.re(result)
                imag = sympy.im(result)

                if self.base != 10 and imag != 0:
                    raise ParseError("Complex number is not allowed in non-decimal mode.")
                else:
                    rstr = self.how_to_display(real)
                    istr = self.how_to_display(imag)
                    if imag == 0:
                        s = rstr
                    elif real == 0:
                        if imag == 1:
                            istr = ""
                        elif imag == -1:
                            istr = "-"

                        s = f"{istr}i"
                    else:
                        if imag == 1 or imag == -1:
                            istr = ""
                        if imag.is_positive:
                            s = f"{rstr} + {istr}i"
                        else:
                            s = f"{rstr} - {istr.lstrip('-')}i"

            if stuff[1]:
                x = var_name
                self.user_variables[x] = result
                results.append(f"{self.base_str}{x} = {s}")
            else:
                results.append(f"{self.base_str}{s}")
        return results

#==================================================================================================================================================

class Calculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.enable_log = bot.enable_calc_log
        except AttributeError:
            self.enable_log = False
        else:
            del bot.enable_calc_log

        self.parsers = data_type.AutoCleanupDict(120, loop=bot.loop)

    def cog_unload(self):
        self.bot.enable_calc_log = self.enable_log
        self.parsers.cleanup()

    def time_stuff(self, func):
        start = time.perf_counter()
        ret = func()
        end = time.perf_counter()
        return ret, end-start

    def get_calc(self, user_id, text):
        try:
            last = self.parsers[user_id]
        except KeyError:
            return MathParse(text)
        else:
            m = MathParse(text)
            m.user_functions.update(last.user_functions)
            m.user_variables.update(last.user_variables)
            return m

    @modding.help(brief="A calculator with loose input rule", category="Misc", field="Processing", paragraph=0)
    @commands.command(aliases=["calc"])
    async def calculate(self, ctx, *, text):
        '''
            `>>calc <formulas>`
            Formulas are separated by linebreak. You can codeblock the whole thing for easier on the eyes.

            **Acceptable expressions:**
             - Operators `+` , `-` , `*` , `/` (true div), `//` (div mod), `%` (mod), `^`|`**` (pow), `!` (factorial)
             - Functions `sin`, `cos`, `tan`, `cot`, `arcsin`|`asin`, `arccos`|`acos`, `arctan`|`atan`, `log` (base 10), `ln` (natural log), `sqrt` (square root), `cbrt` (cube root), `root` (nth root), `abs` (absolute value), `nCk` (combination), `sign`|`sgn` (sign function), `gcd`|`gcf` (greatest common divisor/factor), `lcm` (least common multiple), `max`, `min`, `gamma`, `floor`, `ceil`, `round`
             - Constants `e`, `pi`|`π`, `tau`|`τ`, `i` (imaginary), `inf`|`∞` (infinity, use at your own risk)
             - Enclosed `()`, `[]`, `{}`, `\u2308 \u2309` (ceil), `\u230a \u230b` (floor)
             - Binary/octal/hexadecimal mode. Put `bin:`, `oct:`, `hex:` at the start to use that mode in current line. Default to decimal (`dec:`) mode (well of course)


             - Set a variable to a value (value can be a calculable formula) for next calculations
             - Define a function. User functions must be in `func_name(arg1, arg2...)` format, both at defining and using
             - Special function `sigma`|`Σ` (sum)
                Format: `sigma(n, from, to)(formula)`
                Due to how parser works, n must be a wildcard defined by `n = counter` prior to the sigma function.
             - Special function `reduce` (cumulate)
                Format: `reduce(function, n, from, to)(formula)`
                It's like sigma, but use `function` instead of sum.
                `function` can be either builtin or user-defined, but must take exactly 2 arguments.
             - Line that starts with `#` is comment
        '''
        text = utils.clean_codeblock(text)
        l = ""
        try:
            m = self.get_calc(ctx.author.id, text)
            results, time_taken = await self.bot.loop.run_in_executor(None, self.time_stuff, m.result)
        except ParseError as e:
            target = getattr(e, "target", m)
            await ctx.send(f"{e}\n```\n{target.show_parse_error()}\n```")
        except ZeroDivisionError:
            await ctx.send("Division by zero.")
        except OverflowError:
            await ctx.send("IO number too big. U sure need this one?")
        except ValueError as e:
            target = getattr(e, "target", m)
            await ctx.send(f"Calculation error.\n```\n{target.show_parse_error()}\n```")
            l = traceback.format_exc()
        except Exception as e:
            target = getattr(e, "target", m)
            await ctx.send(f"Parsing error.\n```\n{target.show_parse_error()}\n```")
            l = traceback.format_exc()
        else:
            self.parsers[ctx.author.id] = m
            r = "\n".join(results)
            await ctx.send(f"Result in {1000*(time_taken):.2f}ms\n```\n{r}\n```")
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

    @modding.help(category="Misc", field="Processing", paragraph=0)
    @commands.group()
    async def solve(self, ctx):
        '''
            `>>solve`
            Does nothing actually. This is just the base command.
        '''
        if ctx.invoked_subcommand is None:
            pass

    @modding.help(brief="Solve degree 2 polynominal equation", category="Misc", field="Processing", paragraph=0)
    @solve.command(aliases=["quad", "2nd"])
    async def quadratic(self, ctx, *, stuff):
        '''
            `>>solve quadratic <formulas>`
            Solve quadratic (degree 2) polinominal equation.
            This is an extension of the calculate command. It provides premade solution formulas.
            Input is a serial of formulas that defined `a`, `b` and `c` (as in the equation `ax^2 + bx + c = 0`). Default to 0 if not defined.
        '''
        stuff = utils.clean_codeblock(stuff)
        input = MathParse(stuff)
        try:
            r, input_time = await self.bot.loop.run_in_executor(None, self.time_stuff, input.result)
        except:
            return await ctx.send("Calculation error. Please double check your input.")
        else:
            coefficients = {i: input.user_variables.get(i, 0) for i in ("a", "b", "c", "d")}
            if coefficients["a"] == 0:
                return await ctx.send("Coefficient `a` must be non-zero.")
        solution = MathParse(
            "a = a\n"
            "b = b\n"
            "c = c\n\n"
            "Δ = b^2 - 4ac\n\n"
            "#Result\n"
            "x1 = (-b + sqrt(Δ))/(2a)\n"
            "x2 = (-b - sqrt(Δ))/(2a)"
        )
        solution.user_variables.update(coefficients)
        results, solution_time = await self.bot.loop.run_in_executor(None, self.time_stuff, solution.result)
        r = "\n".join(results[-9:])
        r = f"ax^2 + bx + c = 0\n{r}"
        time_taken = input_time + solution_time
        await ctx.send(f"Result in {1000*(time_taken):.2f}ms\n```\n{r}\n```")

    @modding.help(brief="Solve degree 3 polynominal equation", category="Misc", field="Processing", paragraph=0)
    @solve.command(aliases=["3rd"])
    async def cubic(self, ctx, *, stuff):
        '''
            `>>solve cubic <formulas>`
            Solve quadratic (degree 3) polinominal equation.
            This is an extension of the calculate command. It provides premade solution formulas.
            Input is a serial of formulas that defined `a`, `b`, `c` and `d` (as in the equation `ax^3 + bx^2 + cx + d = 0`). Default to 0 if not defined.
        '''
        stuff = utils.clean_codeblock(stuff)
        input = MathParse(stuff)
        try:
            r, input_time = await self.bot.loop.run_in_executor(None, self.time_stuff, input.result)
        except:
            return await ctx.send("Calculation error. Please double check your input.")
        else:
            coefficients = {i: input.user_variables.get(i, 0) for i in ("a", "b", "c", "d")}
            if coefficients["a"] == 0:
                return await ctx.send("Coefficient `a` must be non-zero.")
        solution = MathParse(
            "ζ1 = -1/2 + sqrt(3)/2 * i\n"
            "ζ2 = -1/2 - sqrt(3)/2 * i\n"
            "a = a\n"
            "b = b\n"
            "c = c\n"
            "d = d\n\n"
            "Δ0 = b^2 - 3ac\n"
            "Δ1 = 2b^3 - 9abc + 27a^2*d\n"
            "C1 = cbrt((Δ1 + sqrt(Δ1^2 - 4Δ0^3))/2)\n"
            "C2 = cbrt((Δ1 - sqrt(Δ1^2 - 4Δ0^3))/2)\n\n"
            "#Result\n"
            "x1 = -(b + C1 + C2)/(3a)\n"
            "x2 = -(b + C1 * ζ1 + C2 / ζ1)/(3a)\n"
            "x3 = -(b + C1 * ζ2 + C2 / ζ2)/(3a)"
        )
        solution.user_variables.update(coefficients)
        results, solution_time = await self.bot.loop.run_in_executor(None, self.time_stuff, solution.result)
        r = "\n".join(results[-14:])
        r = f"ax^3 + bx^2 + cx + d = 0\n{r}"
        time_taken = input_time + solution_time
        await ctx.send(f"Result in {1000*(time_taken):.2f}ms\n```\n{r}\n```")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Calculator(bot))
