from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from . import config, data_type
import asyncio
import math
import random

#==================================================================================================================================================

ANGLE_EPSILON = 0.001

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

    def draw_point(self, xy, *, fill=None, width=1):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        if width < 1:
            self.draw.point(aaxy, fill)
        else:
            half_aawidth = aa * width / 2
            border = (int(aaxy[0]-half_aawidth), int(aaxy[1]-half_aawidth), int(aaxy[0]+half_aawidth), int(aaxy[1]+half_aawidth))
            figure = Image.new("RGBA", self.size, (0, 0, 0, 0))
            fig_draw = ImageDraw.Draw(figure)
            fig_draw.ellipse(border, fill=fill)

            self.image.paste(figure, (0, 0), figure)

    def draw_line(self, xy, *, fill=None, width=1):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        aawidth = aa * width
        self.draw.line(aaxy, fill=fill, width=aawidth)

    def draw_arc(self, xy, start, end, *, fill=None):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        self.draw.arc(aaxy, start, end, fill=fill)

    def draw_rectangle(self, xy, *, fill=None, outline=None, outline_width=0):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        if outline_width < 1 or outline is None:
            self.draw.rectangle(aaxy, fill=fill)
        else:
            aawidth = aa * outline_width
            half_aawidth = aawidth / 2
            half_size = ((aaxy[2]-aaxy[0])/2, (aaxy[3]-aaxy[1])/2)
            center = (aaxy[0]+half_size[0], aaxy[1] + half_size[1])
            outer_border = (int(aaxy[0]-half_aawidth), int(aaxy[1]-half_aawidth), int(aaxy[2]+half_aawidth), int(aaxy[3]+half_aawidth))
            inner_border = (int(aaxy[0]+half_aawidth), int(aaxy[1]+half_aawidth), int(aaxy[2]-half_aawidth), int(aaxy[3]-half_aawidth))

            figure = Image.new("RGBA", self.size, (0, 0, 0, 0))
            fig_draw = ImageDraw.Draw(figure)
            fig_draw.rectangle(outer_border, fill=outline)
            fig_draw.rectangle(inner_border, fill=fill)

            self.image.paste(figure, (0, 0), figure)

    def draw_pieslice(self, xy, start, end, *, fill=None, outline=None, outline_width=0):
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
                if (end - start) % 360 >= ANGLE_EPSILON:
                    dr.line((int_center, arc_start), width=aawidth, fill=o)
                    dr.line((int_center, arc_end), width=aawidth, fill=o)
                    dr.ellipse((int(center[0]-half_aawidth), int(center[1]-half_aawidth), int(center[0]+half_aawidth), int(center[1]+half_aawidth)), fill=o)
                    dr.ellipse((int(arc_start[0]-half_aawidth), int(arc_start[1]-half_aawidth), int(arc_start[0]+half_aawidth), int(arc_start[1]+half_aawidth)), fill=o)
                    dr.ellipse((int(arc_end[0]-half_aawidth), int(arc_end[1]-half_aawidth), int(arc_end[0]+half_aawidth), int(arc_end[1]+half_aawidth)), fill=o)

            self.image.paste(figure, (0, 0), mask)

    def draw_pie_chart(self, xy, cutlist, *, explode=None, outline=None, outline_width=0):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        if outline_width < 1 or outline is None:
            last_angle = cutlist[-1][0]
            for c in cutlist:
                current_angle = c[0]
                self.draw.pieslice(aaxy, last_angle, current_angle, fill=c[1])
                last_angle = current_angle
        else:
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

                    if (ccl[0][0] - start_angle) % 360 < ANGLE_EPSILON:
                        arc_start = (int(center[0]+math.cos(math.radians(start_angle))*half_size[0]), int(center[1]+math.sin(math.radians(start_angle))*half_size[1]))
                        arc_end = (int(center[0]+math.cos(math.radians(last_angle))*half_size[0]), int(center[1]+math.sin(math.radians(last_angle))*half_size[1]))
                        dr.ellipse((int(arc_start[0]-half_aawidth), int(arc_start[1]-half_aawidth), int(arc_start[0]+half_aawidth), int(arc_start[1]+half_aawidth)), fill=o)
                        dr.ellipse((int(arc_end[0]-half_aawidth), int(arc_end[1]-half_aawidth), int(arc_end[0]+half_aawidth), int(arc_end[1]+half_aawidth)), fill=o)
                    else:
                        for c in ccl:
                            current_angle = c[0]
                            fill = c[1]
                            arc_end = (int(center[0]+math.cos(math.radians(current_angle))*half_size[0]), int(center[1]+math.sin(math.radians(current_angle))*half_size[1]))
                            dr.line((arc_end, int_center), width=aawidth, fill=o)
                        dr.ellipse((int(center[0]-half_aawidth), int(center[1]-half_aawidth), int(center[0]+half_aawidth), int(center[1]+half_aawidth)), fill=o)

                self.image.paste(figure, (0, 0), mask)
            else:
                ccl = cutlist.copy()
                last_angle = ccl.pop(0)[0]
                start_angle = last_angle
                for i, c in enumerate(ccl):
                    current_angle = c[0]
                    fill = c[1]
                    delta_angle = current_angle - last_angle
                    if delta_angle >= ANGLE_EPSILON:
                        delta = (math.cos(math.radians(delta_angle/2+last_angle))*explode[i], math.sin(math.radians(delta_angle/2+last_angle))*explode[i])
                        current_xy = (xy[0]+delta[0], xy[1]+delta[1], xy[2]+delta[0], xy[3]+delta[1])
                        self.draw_pieslice(current_xy, last_angle, current_angle, fill=fill, outline=outline, outline_width=outline_width)
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

#==================================================================================================================================================

def adjust_alpha(inp, alpha):
    if inp:
        return (inp[0], inp[1], inp[2], alpha)

async def pie_chart(data, *, unit="counts", background=(255, 255, 255, 0), text_color=(255, 255, 255, 255), outline=None, scale=1, aa=4, explode=None, outline_width=4, loop=None):
    def drawing():
        number_of_fields = len(data)
        number_of_items = sum((d["count"] for d in data))
        if number_of_items == 0:
            return None
        height = max(500, 70+60*number_of_fields)
        image = AAImageProcessing((800, height), background=background, aa=aa)
        image.add_font("normal", f"{config.DATA_PATH}/font/arial.ttf", size=20)
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
        image = AAImageProcessing((720, 400+number_of_fields//2*28), background=background, aa=aa)
        image.add_font("normal", f"{config.DATA_PATH}/font/arial.ttf", size=18)
        image.add_font("axis", f"{config.DATA_PATH}/font/arial.ttf", size=12)
        max_count = max((max(s["count"].values()) for s in data))
        digits = -3
        while max_count >= 10**digits:
            digits += 1
        if max_count < 2*10**(digits-1):
            digits -= 2
        else:
            digits -= 1
        each = 10**digits
        separator_count = 1
        while separator_count*each <= max_count:
            separator_count += 1

        #draw axis
        image.draw_line((50, 10, 50, 350, 670, 350), fill=axis_color)
        image.draw_line((45, 20, 50, 10, 55, 20), fill=axis_color)
        image.draw_line((660, 345, 670, 350, 660, 355), fill=axis_color)
        width, height = image.text_size(unit_y, font="axis")
        image.draw_text((44-width, 4), unit_y, font="axis", fill=axis_text_color)
        width, height = image.text_size(unit_x, font="axis")
        image.draw_text((665, 352), unit_x, font="axis", fill=axis_text_color)
        for i in range(1, separator_count+1):
            v = 350 - i / separator_count * 300
            image.draw_line((45, v, 55, v), fill=axis_color)
            txt = str(each*i)
            width, height = image.text_size(txt, font="axis")
            image.draw_text((42-width, v-height/2-1), txt, font="axis", fill=axis_text_color)

        keys = data[0]["count"].keys()

        for i, k in enumerate(keys):
            h = 50 + (i + 1) * 25
            image.draw_line((h, 345, h, 355), fill=axis_color)
            txt = str(k)
            width, height = image.text_size(txt, font="axis")
            image.draw_text((h-12.5-width/2, 355), txt, font="axis", fill=axis_text_color)

        #draw lines
        for item in data:
            xy = []
            for i, k in enumerate(keys):
                value = item["count"][i]
                xy.append(37.5+(i+1)*25)
                xy.append(350 - value / separator_count / each * 300)
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
