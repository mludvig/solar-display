#!/usr/bin/env python3

import io
import time
import toml
import requests
import digitalio
import board
from PIL import Image, ImageDraw
from adafruit_rgb_display import ili9341

class Display:
    # Config for display baudrate (default max is 24mhz):
    BAUDRATE = 24000000

    def __init__(self):
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
            rotation=270,
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

def fetch_url(url, token):
    print(f"{url=}")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "image/png",
    }

    ts_start = time.time()
    response = requests.get(url, headers = headers)
    if not response.ok:
        print(f"{url}: {response.status_code} {response.reason}")
        print(f"{response.text}")
        return None
    print(f"Load time: {time.time()-ts_start}")

    return response.content


if __name__ == "__main__":
    print(f"Running on: {board.board_id}")
    config = toml.load(open("config.toml"))
    print(f"{config=}")

    disp = Display()

    while True:
        for item in config["url"].items():
            print(f"{item=}")
            url = item[1]["url"]
            #if '{default_params}' in url:
            #    url = url.replace('{default_params}', config["grafana"]["default_params"])
            url = url.format(**config["url_defaults"])
            image_data = fetch_url(url, config['grafana']['token'])
            if image_data is None:
                continue
            image = Image.open(io.BytesIO(image_data))
            disp.display_image(image)
            time.sleep(5)
