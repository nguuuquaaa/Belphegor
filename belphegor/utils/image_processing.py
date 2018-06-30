from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from . import config, data_type
import asyncio
import math
import random
import collections

#==================================================================================================================================================

EPSILON = 0.01

#==================================================================================================================================================

class AAImageProcessing:
    def __init__(self, pred, *, background=(255, 255, 255, 0), aa=4):
        if isinstance(pred, (tuple, list)):
            self.aa = aa
            self.original_size = pred
            self.size = tuple(self.aa*i for i in pred)
            if isinstance(background, tuple):
                self.image = Image.new("RGBA", self.size, background)
            elif isinstance(background, Image.Image):
                self.set_base_image(background)
            else:
                raise TypeError("Background must be a tuple denotes color or an Image object.")
        else:
            self.aa = 1
            self.image = pred
            self.original_size = pred.size
            self.size = self.original_size

        self.draw = ImageDraw.Draw(self.image)
        self.fonts = {}

    def set_base_image(self, image):
        aasize = self.size
        s = image.size
        center = (s[0]/2, s[1]/2)

        scale = min(s[0]/aasize[0], s[1]/aasize[1])
        cut_size = (aasize[0]*scale/2, aasize[1]*scale/2)

        border = (int(center[0]-cut_size[0]), int(center[1]-cut_size[1]), int(center[0]+cut_size[0]), int(center[1]+cut_size[1]))
        border = (max(border[0], 0), max(border[1], 0), min(border[2], aasize[0]), min(border[3], aasize[1]))

        self.image = image.resize(aasize, resample=Image.LANCZOS, box=border)

    def add_font(self, name, *args, size, **kwargs):
        self.fonts[name] = ImageFont.truetype(*args, size*self.aa, **kwargs)

    def save(self, fp, *, format, scale=1, **params):
        im = self.image.resize((int(self.original_size[0]*scale), int(self.original_size[1]*scale)), resample=Image.LANCZOS)
        im.save(fp, format=format, **params)

    def text_size(self, text, *, font, **kwargs):
        font = self.fonts[font]
        aaw, aah = self.draw.textsize(text, font=font, **kwargs)
        return int(aaw/self.aa), int(aah/self.aa)

    def draw_point(self, xy, *, fill, width=1):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        if width < 1:
            self.draw.point(aaxy, fill=fill)
        else:
            half_aawidth = aa * width / 2
            border = (math.ceil(aaxy[0]-half_aawidth), math.ceil(aaxy[1]-half_aawidth), math.floor(aaxy[0]+half_aawidth), math.floor(aaxy[1]+half_aawidth))
            figure = Image.new("RGBA", self.size, (0, 0, 0, 0))
            fig_draw = ImageDraw.Draw(figure)
            fig_draw.ellipse(border, fill=fill)

            self.image.paste(figure, (0, 0), figure)

    def draw_line(self, xy, *, fill, width=1):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        aawidth = aa * width
        draw_border = get_border(aaxy, aa*2)
        draw_size = (draw_border[2]-draw_border[0], draw_border[3]-draw_border[1])

        figure = Image.new("RGBA", draw_size, (0, 0, 0, 0))
        mask = Image.new("L", draw_size, 0)
        draw = (
            (ImageDraw.Draw(figure), adjust_alpha(fill, 255)),
            (ImageDraw.Draw(mask), data_type.get_element(fill, 3, default=255))
        )

        draw_aaxy = tuple(item-draw_border[i%2] for i, item in enumerate(aaxy))
        for value in draw:
            dr = value[0]
            f = value[1]
            dr.line(draw_aaxy, fill=f, width=aawidth)
            if width > 1:
                half_aawidth = aawidth / 2
                for aax, aay in pairwise(draw_aaxy):
                    border = (math.ceil(aax-half_aawidth), math.ceil(aay-half_aawidth), math.floor(aax+half_aawidth), math.floor(aay+half_aawidth))
                    dr.ellipse(border, fill=f)

        self.image.paste(figure, draw_border, mask)

    def draw_arc(self, xy, start, end, *, fill):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        self.draw.arc(aaxy, start, end, fill=fill)

    def draw_rectangle(self, xy, *, fill, outline=None, outline_width=0):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        if outline and outline_width > 0:
            aawidth = aa * outline_width
            half_aawidth = aawidth / 2
            half_size = ((aaxy[2]-aaxy[0])/2, (aaxy[3]-aaxy[1])/2)
            center = (aaxy[0]+half_size[0], aaxy[1] + half_size[1])
            outer_border = (int(aaxy[0]-half_aawidth), int(aaxy[1]-half_aawidth), int(aaxy[2]+half_aawidth), int(aaxy[3]+half_aawidth))
            inner_border = (int(aaxy[0]+half_aawidth), int(aaxy[1]+half_aawidth), int(aaxy[2]-half_aawidth), int(aaxy[3]-half_aawidth))

            draw_size = (outer_border[2]-outer_border[0], outer_border[3]-outer_border[1])
            figure = Image.new("RGBA", draw_size, (0, 0, 0, 0))
            mask = Image.new("L", draw_size, 0)
            draw = (
                (ImageDraw.Draw(figure), adjust_alpha(outline, 255), adjust_alpha(fill, 255)),
                (ImageDraw.Draw(mask), data_type.get_element(outline, 3, default=255), data_type.get_element(fill, 3, default=255))
            )

            for value in draw:
                dr = value[0]
                o = value[1]
                f = value[2]
                draw_outer = tuple(item-outer_border[i%2] for i, item in enumerate(outer_border))
                draw_inner = tuple(item-outer_border[i%2] for i, item in enumerate(inner_border))
                dr.rectangle(draw_outer, fill=o)
                dr.rectangle(draw_inner, fill=f)

            self.image.paste(figure, outer_border, mask)
        else:
            self.draw.rectangle(aaxy, fill=fill)

    def draw_pieslice(self, xy, start, end, *, fill, outline=None, outline_width=0):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        if outline_width < 1 or outline is None:
            self.draw.pieslice(aaxy, start, end, fill=fill)
        else:
            aawidth = aa * outline_width
            half_aawidth = aawidth / 2
            half_size = ((aaxy[2]-aaxy[0])/2, (aaxy[3]-aaxy[1])/2)
            center = (aaxy[0]+half_size[0], aaxy[1] + half_size[1])
            int_center = (int(center[0]), int(center[1]))
            arc_start = (int(center[0]+math.cos(math.radians(start))*half_size[0]), int(center[1]+math.sin(math.radians(start))*half_size[1]))
            arc_end = (int(center[0]+math.cos(math.radians(end))*half_size[0]), int(center[1]+math.sin(math.radians(end))*half_size[1]))
            outer_border = (int(aaxy[0]-half_aawidth), int(aaxy[1]-half_aawidth), int(aaxy[2]+half_aawidth), int(aaxy[3]+half_aawidth))
            inner_border = (int(aaxy[0]+half_aawidth), int(aaxy[1]+half_aawidth), int(aaxy[2]-half_aawidth), int(aaxy[3]-half_aawidth))

            figure = Image.new("RGBA", self.size, (0, 0, 0, 0))
            mask = Image.new("L", self.size, 0)
            draw = (
                (ImageDraw.Draw(figure), adjust_alpha(outline, 255), adjust_alpha(fill, 255)),
                (ImageDraw.Draw(mask), data_type.get_element(outline, 3, default=255), data_type.get_element(fill, 3, default=255))
            )

            for value in draw:
                dr = value[0]
                o = value[1]
                f = value[2]

                dr.pieslice(outer_border, start, end, fill=o)
                dr.pieslice(inner_border, start, end, fill=f)
                if (end - start) % 360 >= EPSILON:
                    dr.line((int_center, arc_start), width=aawidth, fill=o)
                    dr.line((int_center, arc_end), width=aawidth, fill=o)
                    dr.ellipse(
                        (
                            math.ceil(center[0]-half_aawidth),
                            math.ceil(center[1]-half_aawidth),
                            math.floor(center[0]+half_aawidth),
                            math.floor(center[1]+half_aawidth)
                        ),
                        fill=o
                    )
                    dr.ellipse(
                        (
                            math.ceil(arc_start[0]-half_aawidth),
                            math.ceil(arc_start[1]-half_aawidth),
                            math.floor(arc_start[0]+half_aawidth),
                            math.floor(arc_start[1]+half_aawidth)
                        ),
                        fill=o
                    )
                    dr.ellipse(
                        (
                            math.ceil(arc_end[0]-half_aawidth),
                            math.ceil(arc_end[1]-half_aawidth),
                            math.floor(arc_end[0]+half_aawidth),
                            math.floor(arc_end[1]+half_aawidth)
                        ),
                        fill=o
                    )

            self.image.paste(figure, (0, 0), mask)

    def draw_pie_chart(self, xy, cutlist, *, explode=None, outline=None, outline_width=0):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        if outline and outline_width > 0:
            aawidth = aa * outline_width
            half_aawidth = aawidth / 2
            half_size = ((aaxy[2]-aaxy[0])/2, (aaxy[3]-aaxy[1])/2)
            center = (aaxy[0]+half_size[0], aaxy[1]+half_size[1])
            int_center = (int(center[0]), int(center[1]))
            outer_border = (int(aaxy[0]-half_aawidth), int(aaxy[1]-half_aawidth), int(aaxy[2]+half_aawidth), int(aaxy[3]+half_aawidth))
            inner_border = (int(aaxy[0]+half_aawidth), int(aaxy[1]+half_aawidth), int(aaxy[2]-half_aawidth), int(aaxy[3]-half_aawidth))

            if not explode:
                figure = Image.new("RGBA", self.size, (0, 0, 0, 0))
                mask = Image.new("L", self.size, 0)
                draw = (
                    (ImageDraw.Draw(figure), adjust_alpha(outline, 255), lambda f: adjust_alpha(f, 255)),
                    (ImageDraw.Draw(mask), data_type.get_element(outline, 3, default=255), lambda f: data_type.get_element(f, 3, default=255))
                )

                for value in draw:
                    ccl = cutlist.copy()
                    last_angle = ccl.pop(0)[0]
                    start_angle = last_angle
                    dr = value[0]
                    o = value[1]
                    f = value[2]

                    for i, c in enumerate(ccl):
                        current_angle = c[0]
                        fill = c[1]
                        dr.pieslice(outer_border, last_angle, current_angle, fill=o)
                        dr.pieslice(inner_border, last_angle, current_angle, fill=f(fill))
                        last_angle = current_angle

                    if (ccl[0][0] - start_angle) % 360 < EPSILON:
                        arc_start = (int(center[0]+math.cos(math.radians(start_angle))*half_size[0]), int(center[1]+math.sin(math.radians(start_angle))*half_size[1]))
                        arc_end = (int(center[0]+math.cos(math.radians(last_angle))*half_size[0]), int(center[1]+math.sin(math.radians(last_angle))*half_size[1]))
                        dr.ellipse(
                            (
                                math.ceil(arc_start[0]-half_aawidth),
                                math.ceil(arc_start[1]-half_aawidth),
                                math.floor(arc_start[0]+half_aawidth),
                                math.floor(arc_start[1]+half_aawidth)
                            ),
                            fill=o
                        )
                        dr.ellipse(
                            (
                                math.ceil(arc_end[0]-half_aawidth),
                                math.ceil(arc_end[1]-half_aawidth),
                                math.floor(arc_end[0]+half_aawidth),
                                math.floor(arc_end[1]+half_aawidth)
                            ),
                            fill=o
                        )
                    else:
                        for c in ccl:
                            current_angle = c[0]
                            fill = c[1]
                            arc_end = (int(center[0]+math.cos(math.radians(current_angle))*half_size[0]), int(center[1]+math.sin(math.radians(current_angle))*half_size[1]))
                            dr.line((arc_end, int_center), width=aawidth, fill=o)
                        dr.ellipse(
                            (
                                math.ceil(center[0]-half_aawidth),
                                math.ceil(center[1]-half_aawidth),
                                math.floor(center[0]+half_aawidth),
                                math.floor(center[1]+half_aawidth)
                            ),
                            fill=o
                        )

                self.image.paste(figure, (0, 0), mask)
            else:
                ccl = cutlist.copy()
                last_angle = ccl.pop(0)[0]
                start_angle = last_angle
                for i, c in enumerate(ccl):
                    current_angle = c[0]
                    fill = c[1]
                    delta_angle = current_angle - last_angle
                    if delta_angle >= EPSILON:
                        delta = (math.cos(math.radians(delta_angle/2+last_angle))*explode[i], math.sin(math.radians(delta_angle/2+last_angle))*explode[i])
                        current_xy = (xy[0]+delta[0], xy[1]+delta[1], xy[2]+delta[0], xy[3]+delta[1])
                        self.draw_pieslice(current_xy, last_angle, current_angle, fill=fill, outline=outline, outline_width=outline_width)
                    last_angle = current_angle
        else:
            last_angle = cutlist[-1][0]
            for c in cutlist:
                current_angle = c[0]
                self.draw.pieslice(aaxy, last_angle, current_angle, fill=c[1])
                last_angle = current_angle

    def draw_text(self, xy, txt, *, font, **kwargs):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        font = self.fonts[font]
        self.draw.text(aaxy, txt, font=font, **kwargs)

    def circle_paste(self, im, xy):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        aaxy_size = (aaxy[2]-aaxy[0], aaxy[3]-aaxy[1])

        s = im.size
        center = (s[0]/2, s[1]/2)
        radius = min(center)
        border = (int(center[0]-radius), int(center[1]-radius), int(center[0]+radius), int(center[1]+radius))
        border = (max(border[0], 0), max(border[1], 0), min(border[2], s[0]), min(border[3], s[1]))

        mask = Image.new("L", aaxy_size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, *aaxy_size), fill=255)

        resized = im.resize(aaxy_size, resample=Image.LANCZOS, box=border)
        self.image.paste(resized, aaxy, mask)

    def draw_axis(self, root, size, *, x_keys, y_keys, unit_x=None, unit_y=None, color=(150, 150, 150, 255), text_color=(215, 215, 215, 255)):
        x, y = root
        axis_width, axis_height = size
        vec_x = x+axis_width+20
        vec_y = y-axis_height-40

        #base axis
        self.draw_line((x, vec_y, x, y, vec_x, y), fill=color)
        self.draw_line((x-5, vec_y+10, x, vec_y, x+5, vec_y+10), fill=color)
        self.draw_line((vec_x-10, y-5, vec_x, y, vec_x-10, y+5), fill=color)

        #units
        if unit_y:
            width, height = self.text_size(unit_y, font="axis")
            self.draw_text((x-6-width, vec_y-6), unit_y, font="axis", fill=text_color)
        if unit_x:
            width, height = self.text_size(unit_x, font="axis")
            self.draw_text((vec_x-5, y+2), unit_x, font="axis", fill=text_color)

        #marks
        y_count = len(y_keys)
        for i, mark_y in enumerate(y_keys):
            v = y - (i + 1) / y_count * axis_height
            self.draw_line((x-5, v, x+5, v), fill=color)
            txt = f"{mark_y:.2f}".rstrip("0").rstrip(".")
            width, height = self.text_size(txt, font="axis")
            self.draw_text((x-8-width, v-height/2-2), txt, font="axis", fill=text_color)

        x_count = len(x_keys)
        each_width = axis_width / x_count

        for i, k in enumerate(x_keys):
            h = x + (i + 1) * each_width
            self.draw_line((h, y-5, h, y+5), fill=color)
            txt = str(k)
            width, height = self.text_size(txt, font="axis")
            self.draw_text((h-each_width/2-width/2, y+3), txt, font="axis", fill=text_color)

    def draw_polygon(self, xy, *, fill, outline=None, outline_width=0):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        aawidth = aa * outline_width
        draw_border = get_border(aaxy, aa*2)
        draw_size = (draw_border[2]-draw_border[0], draw_border[3]-draw_border[1])

        figure = Image.new("RGBA", draw_size, (0, 0, 0, 0))
        mask = Image.new("L", draw_size, 0)
        draw = (
            (ImageDraw.Draw(figure), adjust_alpha(fill, 255), lambda f: adjust_alpha(f, 255)),
            (ImageDraw.Draw(mask), data_type.get_element(fill, 3, default=255), lambda f: data_type.get_element(f, 3, default=255))
        )

        draw_aaxy = tuple(item-draw_border[i%2] for i, item in enumerate(aaxy))
        for value in draw:
            dr = value[0]
            f = value[1]
            o = value[2]
            dr.polygon(draw_aaxy, fill=f)
            if outline and outline_width > 0:
                dr.line(draw_aaxy, fill=o(outline), width=aawidth)
                dr.line((draw_aaxy[0], draw_aaxy[1], draw_aaxy[-2], draw_aaxy[-1]), fill=o(outline), width=aawidth)
                if outline_width > 1:
                    half_aawidth = aawidth / 2
                    for aax, aay in pairwise(draw_aaxy):
                        border = (math.ceil(aax-half_aawidth), math.ceil(aay-half_aawidth), math.floor(aax+half_aawidth), math.floor(aay+half_aawidth))
                        dr.ellipse(border, fill=o(outline))

        self.image.paste(figure, draw_border, mask)

    def adjust_alpha(self, xy, alpha):
        aaxy = tuple(self.aa*i for i in xy)
        mask = Image.new("L", self.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle(aaxy, fill=alpha)
        self.image.putalpha(mask)

#==================================================================================================================================================

def adjust_alpha(inp, alpha):
    if inp:
        return (inp[0], inp[1], inp[2], alpha)

def pairwise(iterable):
    i = iter(iterable)
    while True:
        yield next(i), next(i)

def get_border(xy, epsilon=1):
    min_x = float("inf")
    min_y = min_x
    max_x = -min_x
    max_y = -min_y
    for x, y in pairwise(xy):
        if x < min_x:
            min_x = x
        if x > max_x:
            max_x = x
        if y < min_y:
            min_y = y
        if y > max_y:
            max_y = y
    return (math.floor(min_x)-epsilon, math.floor(min_y)-epsilon, math.ceil(max_x)+epsilon, math.ceil(max_y)+epsilon)

async def pie_chart(data, *, unit="counts", background=(255, 255, 255, 0), text_color=(255, 255, 255, 255), outline=None, scale=1, aa=4, explode=None, outline_width=4, loop=None):
    def drawing():
        number_of_fields = len(data)
        number_of_items = sum((d["count"] for d in data))
        if number_of_items == 0:
            return None
        height = max(500, 70+60*number_of_fields)
        image = AAImageProcessing((800, height), background=background, aa=aa)
        image.add_font("normal", f"{config.DATA_PATH}/font/arialunicodems.ttf", size=20)
        image.add_font("bold", f"{config.DATA_PATH}/font/arialbd.ttf", size=20)
        cutlist = [(-90, None)]
        current_angle = -90
        for index, item in enumerate(data):
            current_angle = current_angle + 360 * item["count"] / number_of_items
            cutlist.append((current_angle, item["color"]))
            image.draw_rectangle(
                (525, 27+index*60, 550, 52+index*60),
                fill=adjust_alpha(item["color"], 255)
            )
            image.draw_text(
                (560, 30+index*60),
                item["name"],
                font="normal",
                fill=text_color
            )
            count = item["count"]
            if isinstance(count, int):
                s = count
            else:
                s = f"{count:.2f}"
            image.draw_text(
                (560, 55+index*60),
                f"{s} {unit} - {100*count/number_of_items:.2f}%",
                font="normal",
                fill=text_color
            )
        image.draw_pie_chart(
            (40, 40, 460, 460),
            cutlist,
            outline=outline,
            outline_width=outline_width,
            explode=explode
        )

        if isinstance(number_of_items, int):
            s = number_of_items
        else:
            s = f"{number_of_items:.2f}"
        image.draw_text(
            (560, 30+number_of_fields*60),
            f"Total: {s} {unit}",
            font="bold",
            fill=text_color
        )
        bytes_io = BytesIO()
        image.save(bytes_io, format="png", scale=scale)
        return bytes_io.getvalue()

    _loop = loop or asyncio.get_event_loop()
    return await _loop.run_in_executor(None, drawing)

async def line_chart(
    data, *, title=None, unit_y="amount", unit_x="time", background=(255, 255, 255, 0), text_color=(255, 255, 255, 255),
    axis_color=(150, 150, 150, 255), axis_text_color=(215, 215, 215, 255), scale=1, aa=4, loop=None
):
    def drawing():
        number_of_fields = len(data)
        image = AAImageProcessing((720, 400+(number_of_fields+1)//2*28), background=background, aa=aa)
        image.add_font("normal", f"{config.DATA_PATH}/font/arialunicodems.ttf", size=18)
        image.add_font("axis", f"{config.DATA_PATH}/font/arialunicodems.ttf", size=12)

        #calculate marks and draw axis
        max_count = max((max(s["count"].values()) for s in data))
        digits = -3
        while max_count > 10**digits:
            digits += 1
        digits -= 1

        each = 10**digits
        item = 0
        y_keys = []
        while item < max_count:
            item += each
            y_keys.append(item)
        x_keys = data[0]["count"].keys()

        image.draw_axis((50, 350), (600, 300), x_keys=x_keys, y_keys=y_keys, unit_x=unit_x, unit_y=unit_y, color=axis_color, text_color=axis_text_color)

        #draw lines
        each_width = 600 / len(x_keys)
        y_count = len(y_keys)
        for item in data:
            xy = []
            for i, k in enumerate(x_keys):
                value = item["count"][i]
                xy.append(50+(i+1/2)*each_width)
                xy.append(350-value/y_count/each*300)
            image.draw_line(xy, fill=item["color"], width=2)

        #draw legends
        for i, item in enumerate(data):
            x = i % 2 * 300 + 100
            y = i // 2 * 28 + 390
            line_xy = tuple(i for j in range(5) for i in (x+5*j, y+random.randrange(20)))
            image.draw_line(line_xy, fill=item["color"], width=2)
            image.draw_text((x+25, y+1), item["name"], font="normal", fill=text_color)

        if title:
            width, height = image.text_size(title, font="normal")
            image.draw_text((650-width, 10), title, font="normal", fill=text_color)

        bytes_io = BytesIO()
        image.save(bytes_io, format="png", scale=scale)
        return bytes_io.getvalue()

    _loop = loop or asyncio.get_event_loop()
    return await _loop.run_in_executor(None, drawing)

async def stacked_area_chart(
    data, *, title=None, unit_y="amount", unit_x="time", background=(255, 255, 255, 0), text_color=(255, 255, 255, 255),
    axis_color=(200, 200, 200, 255), axis_text_color=(235, 235, 235, 255), scale=1, aa=4, loop=None
):
    def drawing():
        number_of_fields = len(data)
        image = AAImageProcessing((720, 400+(number_of_fields+1)//2*28), background=background, aa=aa)
        image.add_font("normal", f"{config.DATA_PATH}/font/arialunicodems.ttf", size=18)
        image.add_font("axis", f"{config.DATA_PATH}/font/arialunicodems.ttf", size=12)

        #calculate marks
        max_count = max((max(s["count"].values()) for s in data))
        digits = -3
        while max_count > 10**digits + EPSILON:
            digits += 1
        digits -= 1

        each = 10**digits
        item = 0
        y_keys = []
        while item + EPSILON < max_count:
            item += each
            y_keys.append(item)

        #draw all stuff
        arb = data[0]
        x_keys = arb["count"].keys()
        each_width = 600 / len(x_keys)
        y_count = len(y_keys)

        for item in reversed(data):
            xy = [650-each_width/2, 350, 50+each_width/2, 350]
            for i, k in enumerate(x_keys):
                value = item["count"][i]
                xy.append(50+(i+1/2)*each_width)
                xy.append(350-value/y_count/each*300)
            image.draw_polygon(xy, fill=item["color"])

        #draw axis
        image.draw_axis((50, 350), (600, 300), x_keys=x_keys, y_keys=y_keys, unit_x=unit_x, unit_y=unit_y, color=axis_color, text_color=axis_text_color)

        #draw legends
        for i, item in enumerate(data):
            x = i % 2 * 300 + 100
            y = i // 2 * 28 + 390
            image.draw_rectangle((x, y+2, x+20, y+22), fill=item["color"])
            image.draw_text((x+25, y+1), item["name"], font="normal", fill=text_color)

        if title:
            width, height = image.text_size(title, font="normal")
            image.draw_text((650-width, 10), title, font="normal", fill=text_color)

        bytes_io = BytesIO()
        image.save(bytes_io, format="png", scale=scale)
        return bytes_io.getvalue()

    _loop = loop or asyncio.get_event_loop()
    return await _loop.run_in_executor(None, drawing)

async def bar_chart(
    data, *, title=None, unit_y="amount", unit_x="time", background=(255, 255, 255, 0), text_color=(255, 255, 255, 255),
    axis_color=(200, 200, 200, 255), axis_text_color=(235, 235, 235, 255), scale=1, aa=4, loop=None
):
    def drawing():
        number_of_fields = len(data)
        x_keys = data[0]["count"].keys()
        number_of_marks = len(x_keys)
        if number_of_marks > 15:
            axis_width = 40*number_of_marks
        else:
            axis_width = 600
        image = AAImageProcessing((120+axis_width, 400+(number_of_fields+1)//2*28), background=background, aa=aa)
        image.add_font("normal", f"{config.DATA_PATH}/font/arialunicodems.ttf", size=18)
        image.add_font("axis", f"{config.DATA_PATH}/font/arialunicodems.ttf", size=12)

        #calculate marks and draw axis
        max_count = max((max(s["count"].values()) for s in data))
        digits = -3
        while max_count > 10**digits:
            digits += 1
        digits -= 1

        each = 10**digits
        item = 0
        y_keys = []
        while item < max_count:
            item += each
            y_keys.append(item)

        image.draw_axis((50, 350), (axis_width, 300), x_keys=x_keys, y_keys=y_keys, unit_x=unit_x, unit_y=unit_y, color=axis_color, text_color=axis_text_color)

        #draw bars
        each_width = axis_width / len(x_keys)
        each_bar = each_width * 0.8 / number_of_fields
        y_count = len(y_keys)
        for index, item in enumerate(data):
            for i, k in enumerate(x_keys):
                value = item["count"][i]
                x = 50 + each_width * i + each_width / 10 + each_bar * index
                y = 350-value/y_count/each*300
                image.draw_rectangle((x, y, x+each_bar, 350), fill=item["color"])

        #draw legends
        for i, item in enumerate(data):
            x = i % 2 * 300 + 100
            y = i // 2 * 28 + 390
            image.draw_rectangle((x, y+2, x+20, y+22), fill=item["color"])
            image.draw_text((x+25, y+1), item["name"], font="normal", fill=text_color)

        if title:
            width, height = image.text_size(title, font="normal")
            image.draw_text((axis_width+50-width, 10), title, font="normal", fill=text_color)

        bytes_io = BytesIO()
        image.save(bytes_io, format="png", scale=scale)
        return bytes_io.getvalue()

    _loop = loop or asyncio.get_event_loop()
    return await _loop.run_in_executor(None, drawing)
