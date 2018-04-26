from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from . import config, data_type
import asyncio
import math

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

    def set_base_image(self, image):
        aasize = self.size
        s = image.size
        center = (s[0]/2, s[1]/2)

        scale = min(s[0]/aasize[0], s[1]/aasize[1])
        cut_size = (aasize[0]*scale/2, aasize[1]*scale/2)

        border = (int(center[0]-cut_size[0]), int(center[1]-cut_size[1]), int(center[0]+cut_size[0]), int(center[1]+cut_size[1]))
        border = (max(border[0], 0), max(border[1], 0), min(border[2], aasize[0]), min(border[3], aasize[1]))

        self.image = image.resize(aasize, resample=Image.LANCZOS, box=border)

    def save(self, fp, *, format, scale=1, **params):
        im = self.image.resize((int(self.original_size[0]*scale), int(self.original_size[1]*scale)), resample=Image.LANCZOS)
        im.save(fp, format=format, **params)

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

                for c in ccl:
                    current_angle = c[0]
                    fill = c[1]
                    dr.pieslice(outer_border, last_angle, current_angle, fill=o)
                    dr.pieslice(inner_border, last_angle, current_angle, fill=f(fill))
                    last_angle = current_angle

                for c in ccl:
                    current_angle = c[0]
                    fill = c[1]
                    arc_end = (int(center[0]+math.cos(math.radians(current_angle))*half_size[0]), int(center[1]+math.sin(math.radians(current_angle))*half_size[1]))
                    dr.line((arc_end, int_center), width=aawidth, fill=o)

                if (last_angle - start_angle) % 360 < 0.01:
                    arc_start = (int(center[0]+math.cos(math.radians(start_angle))*half_size[0]), int(center[1]+math.sin(math.radians(start_angle))*half_size[1]))
                    arc_end = (int(center[0]+math.cos(math.radians(last_angle))*half_size[0]), int(center[1]+math.sin(math.radians(last_angle))*half_size[1]))
                    dr.ellipse((int(arc_start[0]-half_aawidth), int(arc_start[1]-half_aawidth), int(arc_start[0]+half_aawidth), int(arc_start[1]+half_aawidth)), fill=o)
                    dr.ellipse((int(arc_end[0]-half_aawidth), int(arc_end[1]-half_aawidth), int(arc_end[0]+half_aawidth), int(arc_end[1]+half_aawidth)), fill=o)

                dr.ellipse((int(center[0]-half_aawidth), int(center[1]-half_aawidth), int(center[0]+half_aawidth), int(center[1]+half_aawidth)), fill=o)

            self.image.paste(figure, (0, 0), mask)

    def draw_text(self, xy, txt, **kwargs):
        aa = self.aa
        aaxy = tuple(aa*i for i in xy)
        self.draw.text(aaxy, txt, **kwargs)

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

async def pie_chart(data, *, unit="counts", background=(255, 255, 255, 0), text_color=(255, 255, 255, 255), outline=None, scale=1, aa=4, loop=None):
    def drawing():
        number_of_fields = len(data)
        number_of_items = sum((d["count"] for d in data))
        if number_of_items == 0:
            return None
        height = max(500, 70+60*number_of_fields)
        image_draw = AAImageProcessing((800, height), background=background, aa=aa)
        font = ImageFont.truetype(f"{config.DATA_PATH}/font/arial.ttf", 20*aa)
        big_font = ImageFont.truetype(f"{config.DATA_PATH}/font/arialbd.ttf", 20*aa)
        cutlist = [(-90, None)]
        current_angle = -90
        for index, item in enumerate(data):
            current_angle = current_angle + 360 * item["count"] / number_of_items
            cutlist.append((current_angle, item["color"]))
            image_draw.draw_rectangle(
                (525, 27+index*60, 550, 52+index*60),
                fill=adjust_alpha(item["color"], 255)
            )
            image_draw.draw_text(
                (560, 30+index*60),
                item["name"],
                font=font,
                fill=text_color
            )
            image_draw.draw_text(
                (560, 55+index*60),
                f"{item['count']} {unit} - {100*item['count']/number_of_items:.2f}%",
                font=font,
                fill=text_color
            )
        image_draw.draw_pie_chart(
            (40, 40, 460, 460),
            cutlist,
            outline=outline,
            outline_width=5,
        )
        image_draw.draw_text(
            (560, 30+number_of_fields*60),
            f"Total: {number_of_items} {unit}",
            font=big_font,
            fill=text_color
        )
        bytes_io = BytesIO()
        image_draw.save(bytes_io, format="png", scale=scale)
        return bytes_io.getvalue()

    _loop = loop or asyncio.get_event_loop()
    return await _loop.run_in_executor(None, drawing)
