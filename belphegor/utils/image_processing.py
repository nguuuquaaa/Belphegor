from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from . import config
import asyncio

#==================================================================================================================================================

async def pie_chart(data, *, unit="counts", bg_color=(255, 255, 255, 0), text_color=(255, 255, 255, 255), scale=1, aa=4, loop=None):
    def drawing():
        number_of_fields = len(data)
        number_of_items = sum((d["count"] for d in data))
        if number_of_items == 0:
            return None
        pic = Image.new('RGBA', (aa*800, aa*max(500, 70 + 60*number_of_fields)), bg_color)
        font = ImageFont.truetype(f"{config.DATA_PATH}/font/arial.ttf", aa*20)
        big_font = ImageFont.truetype(f"{config.DATA_PATH}/font/arialbd.ttf", aa*20)
        draw = ImageDraw.Draw(pic)
        prev_angle = 0
        for index, item in enumerate(data):
            cur_angle = prev_angle + 360*item["count"]/number_of_items
            draw.pieslice(
                (aa*20, aa*20, aa*480, aa*480),
                -90.0+prev_angle,
                -90.0+cur_angle,
                fill=item["color"]
            )
            draw.rectangle(
                (aa*525, aa*(27+index*60), aa*550, aa*(52+index*60)),
                fill=item["color"]
            )
            draw.text(
                (aa*560, aa*(30+index*60)),
                item["name"],
                font=font,
                fill=text_color
            )
            draw.text(
                (aa*560, aa*(55+index*60)),
                f"{item['count']} {unit} - {100*item['count']/number_of_items:.2f}%",
                font=font,
                fill=text_color
            )
            prev_angle = cur_angle
        draw.text(
            (aa*560, aa*(30+number_of_fields*60)),
            f"Total: {number_of_items} {unit}",
            font=big_font,
            fill=text_color
        )
        if aa > scale or scale < 1:
            resized_pic = pic.resize((int(800*scale), int(max(500, 70 + 60*number_of_fields)*scale)), resample=Image.HAMMING)
        else:
            resized_pic = pic
        bytes_io = BytesIO()
        resized_pic.save(bytes_io, format="png")
        return bytes_io.getvalue()

    _loop = loop or asyncio.get_event_loop()
    return await _loop.run_in_executor(None, drawing)
