#!/usr/bin/env python3

import io
import time
import asyncio
import queue

import board
import yaml
import aiohttp

from PIL import Image, ImageDraw, ImageFont

from display import Display
from touch import TouchScreen

BUZZER_PIN=17

touch_queue = queue.Queue(1)

async def fetch_one_url(session, url, url_id, headers):
    tries = 5
    while tries:
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.ok:
                    return {
                        "id": url_id,
                        "content": await resp.read(),
                    }
                print(f"ERROR {url} : status={resp.status} ({resp.reason})")
        except Exception as ex:
            print(f"ERROR {url} : {ex}")
        tries -= 1
        await asyncio.sleep(0.5)
    return {
        "id": url_id,
        "content": None,
    }

async def fetch_urls(urls, token):
    """
    Fetch the "urls" and return the data.
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

    # Convert to dict with 'id' as the key
    data = { item["id"]: item for item in data_raw }

    return data


def wait_screen(disp, message = "Please wait..."):
    dashboard_image = Image.new("RGB", (disp.d_width, disp.d_height), "#000")
    draw = ImageDraw.Draw(dashboard_image)
    font = ImageFont.truetype("fonts/Roboto-Regular.ttf", 32)
    draw.text((10, disp.d_height//3), message, font=font, fill="#FF0")
    disp.display_image(dashboard_image)

def error_tile():
    error_image = Image.new("RGB", (30, 30), "#FFF")
    draw = ImageDraw.Draw(error_image)
    font = ImageFont.truetype("fonts/Roboto-Regular.ttf", 30)
    draw.text((1, 1), "X", font=font, fill="#A00")
    return error_image

class DashboardManager:
    def __init__(self, config, disp):
        self.config = config
        self.current_dashboard = None
        self.disp = disp

    def find_dashboard(self, dash_name):
        if dash_name not in self.config["dashboards"]:
            raise ValueError(f"Dashboard not found: {dash_name}")
        return self.config["dashboards"][dash_name]

    def show_dashboard(self, dash_name):
        self.current_dashboard = self.find_dashboard(dash_name)
        urls = []
        for tile in self.current_dashboard["tiles"]:
            urls.append({
                "id": tile["id"],
                "url": tile["url"]
            })
        #print("Starting to download URLs...")
        data = asyncio.run(fetch_urls(urls, self.config['general']['grafana_token']))

        dashboard_image = Image.new("RGB", (self.disp.d_width, self.disp.d_height), "#FFF")
        for tile in self.current_dashboard["tiles"]:
            try:
                image = Image.open(io.BytesIO(data[tile["id"]]["content"]))
            except Exception as ex:
                print(f"ERROR: {ex}")
                image = error_tile()
                # Never mind, move on...
            dashboard_image.paste(image, tile.get("placement", (0,0)))

        self.disp.display_image(dashboard_image)
        return self.current_dashboard.get("touch_areas", None)

    def resolve_touch(self, touch_coords):
        if self.current_dashboard is None or "touch_areas" not in self.current_dashboard:
            return None
        for area in self.current_dashboard["touch_areas"]:
            box = area["box"]
            if box[0] <= touch_coords[0] <= box[2] and box[1] <= touch_coords[1] <= box[3]:
                return area["id"]
        print(f"WARNING: Touch ({touch_coords[0]},{touch_coords[1]}) does not belong to any defined area!")
        return None

def main():
    print(f"Running on: {board.board_id}")

    with open("config.yaml") as f:
        # First we only need the "defaults" section
        config_yaml = f.read()
        config = yaml.safe_load(config_yaml)
        # Now substitute (aka "format()") the defaults to the config.yaml
        config_yaml = config_yaml.format(**config["defaults"])
        config = yaml.safe_load(config_yaml)

    disp = Display(rotation=config["general"]["rotation"])
    wait_screen(disp)

    dash_manager = DashboardManager(config, disp)

    touch_screen = TouchScreen(touch_queue, BUZZER_PIN, config["general"]["rotation"])

    dash_change_timestamp = time.time()
    dash_revert_timeout = 60*5      # seconds

    dash_name_default = "main"
    dash_name = dash_name_default
    while True:
        if time.time() - dash_change_timestamp > dash_revert_timeout:
            dash_name = dash_name_default
            dash_change_timestamp = time.time()
        touch_areas = dash_manager.show_dashboard(dash_name)
        try:
            touch_coords = touch_queue.get(timeout=5)
        except queue.Empty:
            continue
        new_dash_name = dash_manager.resolve_touch(touch_coords)
        print(f"Switching to dashboard: {new_dash_name}")
        if new_dash_name is not None:
            dash_name = new_dash_name
            dash = dash_manager.find_dashboard(dash_name)
            wait_screen(disp, message=f"Loading dashboard:\n{dash.get('label', dash_name)}")
            dash_change_timestamp = time.time()
