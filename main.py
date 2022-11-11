#!/usr/bin/env python3

import io
import time
import asyncio

import yaml
import aiohttp
import digitalio
import board

from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import ili9341

class Display:
    # Config for display baudrate (default max is 24mhz):
    BAUDRATE = 24000000

    def __init__(self, rotation=0):
        # Configuration for CS and DC pins (these are PiTFT defaults):
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = digitalio.DigitalInOut(board.D24)
        backlight_pin = digitalio.DigitalInOut(board.D23)

        # Turn on the Backlight
        backlight_pin.switch_to_output()
        backlight_pin.value = True

        # Setup SPI bus using hardware SPI:
        spi = board.SPI()

        # Create the display:
        self.disp = ili9341.ILI9341(
            spi,
            rotation=rotation,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=self.BAUDRATE,
        )


        # Create blank image for drawing.
        # Make sure to create image with mode 'RGB' for full color.
        if self.disp.rotation % 180 == 90:
            # landscape mode
            self.d_height = self.disp.width
            self.d_width = self.disp.height
        else:
            # portrait mode
            self.d_height = self.disp.height
            self.d_width = self.disp.width

    def display_image(self, image):
        # Crop oversized image
        if image.height > self.d_height or image.width > self.d_width:
            image = image.crop((0, 0, self.d_width, self.d_height))

        # Display image.
        self.disp.image(image)


async def fetch_one_url(session, url, url_id, headers):
    print(f"{url=}")
    async with session.get(url, headers=headers) as resp:
        return {
            "id": url_id,
            "status": resp.status,
            "content": await resp.read(),
        }

async def fetch_urls(urls, token):
    """
    Fetch the "urls" and return the data.

    Parameters:
        urls: dict of dicts
            {
                "id1": { "url": "http://..." },
                "id2": { "url": "http://..." },
            }
        token: str
            Grafana service account token, e.g. "gsat_xyzabcd"

    Returns:
        dict of dicts:
            {
                "id1": { "status": 200, "content": ... },
                "id2": { "status": 500, "content": None },
            }
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "image/png",
    }

    ts_start = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for item in urls:
            url_id = item["id"]
            url = item["url"]
            tasks.append(asyncio.ensure_future(fetch_one_url(session, url, url_id, headers)))
        data_raw = await asyncio.gather(*tasks)

    print(f"Load time: {time.time()-ts_start}")

    # Convert to dict with 'id' as the key
    data = { item["id"]: item for item in data_raw }

    return data


def build_wait_screen(width, height):
    dashboard_image = Image.new("RGB", (width, height), "#000")
    draw = ImageDraw.Draw(dashboard_image)
    font = ImageFont.truetype("fonts/Roboto-Regular.ttf", 40)
    draw.text((10, 10), "Please wait ...", font=font, fill="#FF0")
    return dashboard_image

def build_dashboard(dashboard, width, height):
    urls = []
    for item in dashboard.items():
        if type(item[1]) == dict and "url" in item[1]:
            urls.append({
                "id": item[0],
                "url": item[1]["url"]
            })
    data = asyncio.run(fetch_urls(urls, config['general']['grafana_token']))

    dashboard_image = Image.new("RGB", (width, height), "#FFF")
    for item in dashboard.items():
        if type(item[1]) == dict:
            try:
                image = Image.open(io.BytesIO(data[item[0]]["content"]))
                dashboard_image.paste(image, item[1].get("placement", (0,0)))
            except Exception as ex:
                print(f"ERROR: {ex}")
                # Never mind, move on...

    return dashboard_image
 
if __name__ == "__main__":
    print(f"Running on: {board.board_id}")
    config = yaml.safe_load(open("config.yaml"))

    disp = Display(rotation=config["general"]["rotation"])
    disp.display_image(build_wait_screen(disp.d_width, disp.d_height))

    print("Loading dashboards...")
    dashboards = {}
    for dashboard_name in filter(lambda x: x.startswith("dashboard-"), config.keys()):
        dashboard_name = dashboard_name.replace("dashboard-", "")
        print(f"* {dashboard_name}")
        dashboards[dashboard_name] = {}
        for item in config[f"dashboard-{dashboard_name}"].items():
            dashboards[dashboard_name][item[0]] = item[1]
            if "url" in dashboards[dashboard_name][item[0]]:
                dashboards[dashboard_name][item[0]]["url"] = item[1]["url"].format(**config["url_defaults"])

    #print(json.dumps(dashboards, indent=2))

    while True:
        image = build_dashboard(dashboards["main"], disp.d_width, disp.d_height)
        disp.display_image(image)
        time.sleep(10)

        #image = build_dashboard(dashboards["impexp"], disp.d_width, disp.d_height)
        #disp.display_image(image)
        #time.sleep(10)
