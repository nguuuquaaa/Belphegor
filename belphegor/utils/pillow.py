from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from . import config
import asyncio

_loop = asyncio.get_event_loop()

async def pie_chart(data, *, unit="counts", aa=4):
    def drawing():
        number_of_fields = len(data)
        number_of_items = sum((d["count"] for d in data))
        if number_of_items == 0:
            return None
        pic = Image.new('RGB', (aa*800, aa*max(500, 70 + 60*number_of_fields)), (255, 255, 255))
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
                fill=(0, 0, 0)
            )
            draw.text(
                (aa*560, aa*(55+index*60)),
                f"{item['count']} {unit} - {100*item['count']/number_of_items:.2f}%",
                font=font,
                fill=(0, 0, 0)
            )
            prev_angle = cur_angle
        draw.text(
            (aa*560, aa*(30+number_of_fields*60)),
            f"Total: {number_of_items} {unit}",
            font=big_font,
            fill=(0, 0, 0)
        )
        if aa > 1:
            resized_pic = pic.resize((800, max(500, 70 + 60*number_of_fields)), resample=Image.HAMMING)
        else:
            resized_pic = pic
        bytes_io = BytesIO()
        resized_pic.save(bytes_io, format="png")
        return bytes_io.getvalue()

    return await _loop.run_in_executor(None, drawing)