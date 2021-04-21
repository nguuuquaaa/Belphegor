from . import string_utils
import functools
import hashlib
import collections

#==================================================================================================================================================

def generate_image_path(filename):
    filename = filename.replace(" ", "_")
    name_hash = hashlib.md5(filename.encode("utf-8")).hexdigest()
    return f"images/{name_hash[0]}/{name_hash[:2]}/{filename}"

#==================================================================================================================================================

class ParsingError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class NotABox(ParsingError):
    pass

class HTMLTag(collections.UserDict):
    pass

#==================================================================================================================================================

class WikitextParser:
    def __init__(self):
        self.box_parsers = {}
        self.html_parser = self.html_do_nothing
        self.reference_parser = self.reference_do_nothing
        self.table_parsers = {}

    def log_this(name):
        def wrapper(func):
            @functools.wraps(func)
            def new_func(self, *args, **kwargs):
                self.logs.append(f"{self.indent*' '}start {name}")
                self.indent += 4
                ret = func(self, *args, **kwargs)
                self.logs.append(f"{self.indent*' '}value of {name}: {ret}")
                self.indent -= 4
                self.logs.append(f"{self.indent*' '}end {name}")
                return ret
            return new_func
        return wrapper

    def box_do_nothing(self, box, *args, **kwargs):
        return f"{{{{{box}|{'|'.join(args)}|{'|'.join(f'{k}={v}' for k, v in kwargs.items())}}}}}"

    def set_box_handler(self, box):
        def wrapper(func):
            if box is None:
                self.box_do_nothing = func
            else:
                self.box_parsers[box.lower()] = func
            return func
        return wrapper

    def _join_values(self, value):
        ret = []
        cur = []
        joinable = True
        for v in value:
            if isinstance(v, str):
                cur.append(v)
            else:
                joinable = False
                if cur:
                    ret.append("".join(cur))
                    cur.clear()
                ret.append(v)
        if cur:
            ret.append("".join(cur))
        if joinable:
            return "".join(ret).strip()
        else:
            if isinstance(ret[0], str):
                ret[0] = ret[0].lstrip()
            if isinstance(ret[-1], str):
                ret[-1] = ret[-1].rstrip()
            return [r for r in ret if r]

    @log_this("curly")
    def _parse_curly(self, text_iter):
        next_char = next(text_iter)
        if next_char == "|":
            return self._parse_table(text_iter)
        elif next_char != "{":
            return "{" + next_char
        else:
            args = []
            kwargs = {}
            value = []
            key = None
            ref = 0
            while True:
                next_char = self._parse_next(text_iter)
                if next_char == "=":
                    if key is None:
                        key = self._join_values(value).lower()
                        value.clear()
                    else:
                        value.append(next_char)
                elif next_char == "|":
                    if ref >= 2:
                        value.append(next_char)
                    else:
                        if key is None:
                            args.append(self._join_values(value))
                        else:
                            kwargs[key] = self._join_values(value)
                        value.clear()
                        key = None
                elif next_char == "}":
                    next_char = next(text_iter)
                    if next_char != "}":
                        value.append("}"+next_char)
                    else:
                        if value:
                            if key is None:
                                args.append(self._join_values(value))
                            else:
                                kwargs[key] = self._join_values(value)
                        box = args[0]
                        return self.box_parsers.get(box.lower(), self.box_do_nothing)(*args, **kwargs)
                else:
                    value.append(next_char)

    def table_do_nothing(self, class_, table):
        return table

    def set_table_handler(self, class_):
        def wrapper(func):
            if class_ is None:
                self.table_do_nothing = func
            else:
                self.table_parsers[class_] = func
            return func
        return wrapper

    @log_this("table")
    def _parse_table(self, text_iter):
        table = []
        while True:
            next_char = next(text_iter)
            if next_char == "|":
                next_char = next(text_iter)
                if next_char == "}":
                    break
                else:
                    table.append("|" + next_char)
            else:
                table.append(next_char)
        table = "".join(table).split("\n")

        # table header
        ti = iter(table[0])
        key = ""
        value = next_char
        header = {}
        while True:
            try:
                next_char = next(ti)
            except StopIteration:
                if key or value:
                    header[key] = value
                break

            if next_char == "=":
                if key:
                    value = value + next_char
                else:
                    key = value
                    value = ""
            elif next_char == "\"":
                quote_words = []
                escape = False
                while True:
                    w = next(ti)
                    if escape:
                        quote_words.append(w)
                        escape = False
                    elif w == "\"":
                        value = "".join(quote_words)
                        break
                    else:
                        if w == "\\":
                            escape = True
                        quote_words.append(w)
            elif not next_char.isspace():
                value = value + next_char
            else:
                if key:
                    pass
                else:
                    header[key] = value
                    key = ""
                    value = ""
        # end header

        ret = []
        row = [""]
        for raw in table[1:]:
            if raw.startswith("!"):
                row[0] = raw[1:].rpartition("|")[2].strip()
            elif raw.startswith("|-"):
                ret.append(row)
                row = [""]
            elif raw.startswith("|"):
                row.extend(c.strip() for c in raw[1:].split("||"))
                if len(row) > 1:
                    row[1] = row[1].rpartition("|")[2].strip()
            else:
                row[-1] = f"{row[-1]}\n{raw}".strip()
        if len(row) > 1:
            ret.append(row)
        
        class_ = header.get("class")
        return self.table_parsers.get(class_, self.table_do_nothing)(class_, ret)

    def reference_do_nothing(self, *args, **kwargs):
        return f"[[" + "|".join((*(str(a) for a in args), *(f"{k}={v}" for k, v in kwargs.items()))) + "]]"

    def set_reference_handler(self, func):
        self.reference_parser = func
        return func

    @log_this("bracket")
    def _parse_bracket(self, text_iter):
        next_char = next(text_iter)
        if next_char != "[":
            return "[" + next_char
        else:
            args = []
            kwargs = {}
            value = []
            key = None
            while True:
                next_char = self._parse_next(text_iter)
                if next_char == "=":
                    if key is None:
                        key = self._join_values(value).lower()
                        value.clear()
                    else:
                        value.append(next_char)
                elif next_char == "|":
                    if key is None:
                        args.append(self._join_values(value))
                    else:
                        kwargs[key] = self._join_values(value)
                    value.clear()
                    key = None
                elif next_char == "]":
                    next_char = next(text_iter)
                    if next_char != "]":
                        value.append("]"+next_char)
                    else:
                        if key or value:
                            if key is None:
                                args.append(self._join_values(value))
                            else:
                                kwargs[key] = self._join_values(value)
                        return self.reference_parser(*args, **kwargs)
                else:
                    value.append(next_char)
        
    @log_this("next")
    def _parse_next(self, text_iter):
        next_char = next(text_iter)
        if next_char == "{":
            return self._parse_curly(text_iter)
        elif next_char == "[":
            return self._parse_bracket(text_iter)
        elif next_char == "<":
            return self._parse_xml(text_iter)
        elif next_char == "'":
            return self._parse_raw(text_iter)
        else:
            return next_char
            
    def html_do_nothing(self, tag, text, **kwargs):
        return text

    def set_html_handler(self, func):
        self.html_parser = func
        return func

    @log_this("xml")
    def _parse_xml(self, text_iter):
        def _parse_tag(text_iter):
            next_char = next(text_iter)
            if next_char.isalpha():
                key = ""
                tag = HTMLTag()
                value = next_char
                while True:
                    next_char = next(text_iter)
                    if next_char == ">":
                        if key:
                            tag[key] = value
                        elif value:
                            if "" in tag:
                                tag[value] = ""
                            else:
                                tag[""] = value
                        break
                    elif next_char == "=":
                        if key:
                            value = value + next_char
                        else:
                            key = value
                            value = ""
                    elif next_char == "\"":
                        quote_words = []
                        escape = False
                        keep_going = True
                        while keep_going:
                            w = next(text_iter)
                            if escape:
                                quote_words.append(w)
                                escape = False
                            elif w == "\"":
                                value = "".join(quote_words)
                                break
                            elif w == ">":
                                value = "".join(quote_words)
                                if key or value:
                                    tag[key] = value
                                keep_going = False
                            else:
                                if w == "\\":
                                    escape = True
                                quote_words.append(w)
                        if not keep_going:
                            break
                    elif next_char == "/":
                        next_char = next(text_iter)
                        if next_char == ">":
                            if key or value:
                                tag[key] = value
                            tag["//"] = tag.pop("", "")
                            break
                        else:
                            value = value + "/" + next_char
                    elif not next_char.isspace():
                        value = value + next_char
                    else:
                        if key:
                            pass
                        else:
                            if not key and "" in tag:
                                tag[value] = ""
                            else:
                                tag[key] = value
                                key = ""
                                value = ""
                
                return tag
            
            elif next_char == "/":
                value = ""
                while True:
                    next_char = next(text_iter)
                    if next_char == ">":
                        break
                    else:
                        value = value + next_char

                return HTMLTag({"/": value})

            elif next_char == "!":
                # this is actually a damn comment
                while True:
                    next_char = next(text_iter)
                    if next_char == ">":
                        raise NotABox("")

            else:
                raise NotABox("<"+next_char)

        try:
            open_tag = _parse_tag(text_iter)
        except NotABox as e:
            return e.message
        self.logs.append(f"{self.indent*' '}open tag: {open_tag}")
        
        malformed = open_tag.get("//")
        if malformed == "br":
            return "\n"
        elif malformed:
            return ""

        end = open_tag.get("/")
        if end == "br":
            return "\n"
        elif end:
            return open_tag
        else:
            value = []
            while True:
                next_char = self._parse_next(text_iter)
                self.logs.append(f"{self.indent*' '}text: {next_char}")
                if isinstance(next_char, HTMLTag):
                    end = next_char["/"]
                    if end == open_tag[""]:
                        open_tag.pop("")
                        return self.html_parser(end, self._join_values(value), **open_tag)
                    else:
                        raise ParsingError("Fucked HTML tags.")
                else:
                    value.append(next_char)

    @log_this("2quotes")
    def _parse_raw(self, text_iter):
        next_char = next(text_iter)
        if next_char != "'":
            return "'" + next_char
        else:
            bold = None
            args = []
            kwargs = {}
            value = []
            key = None
            while True:
                next_char = next(text_iter)
                if next_char == "'":
                    if bold is None:
                        bold = True
                        continue
                    next_char = next(text_iter)
                    if next_char != "'":
                        value.append("'"+next_char)
                    else:
                        if bold:
                            next_char = next(text_iter)
                            if next_char != "'":
                                value.append("'"+next_char)
                            else:
                                return "".join(value).strip()
                        else:
                            return "".join(value).strip()
                else:
                    if bold is None:
                        bold = False
                    value.append(next_char)

    def parse(self, text, with_logs=False):
        self.logs = []
        self.indent = 0
        ret = []
        text_iter = string_utils.split_iter(text, check=lambda x: x.isspace() or x in ("{", "}", "[", "]", "<", ">", "=", "\"", "/", "|", "!", "'"))
        while True:
            try:
                next_word = self._parse_next(text_iter)
            except StopIteration:
                if with_logs:
                    return self._join_values(ret), self.logs
                else:
                    return self._join_values(ret)
            else:
                ret.append(next_word)
