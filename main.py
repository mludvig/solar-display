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

BUZZER_PIN=2

touch_queue = queue.Queue(1)

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

class DashboardManager:
    def __init__(self, dashboards, disp):
        self.dashboards = dashboards
        self.current_dashboard = None
        self.disp = disp

    def find_dashboard(self, dash_name):
        if dash_name not in self.dashboards:
            raise ValueError(f"Dashboard not found: {dash_name}")
        return self.dashboards[dash_name]

    def show_dashboard(self, dash_name):
        self.current_dashboard = self.find_dashboard(dash_name)
        urls = []
        for tile in self.current_dashboard["tiles"]:
            urls.append({
                "id": tile["id"],
                "url": tile["url"]
            })
        data = asyncio.run(fetch_urls(urls, config['general']['grafana_token']))

        dashboard_image = Image.new("RGB", (self.disp.d_width, self.disp.d_height), "#FFF")
        for tile in self.current_dashboard["tiles"]:
            try:
                image = Image.open(io.BytesIO(data[tile["id"]]["content"]))
                dashboard_image.paste(image, tile.get("placement", (0,0)))
            except Exception as ex:
                print(f"ERROR: {ex}")
                # Never mind, move on...

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

if __name__ == "__main__":
    print(f"Running on: {board.board_id}")

    with open("config.yaml") as f:
        # First we only need the "defaults" section
        config_yaml = f.read()
        config = yaml.safe_load(config_yaml)
        # Now substitute (aka "format()") the defaults to the config.yaml
        config_yaml = config_yaml.format(**config["defaults"])
        config = yaml.safe_load(config_yaml)

    disp = Display(rotation=config["general"]["rotation"])
    disp.display_image(build_wait_screen(disp.d_width, disp.d_height))
    dash_manager = DashboardManager(config["dashboards"], disp)

    touch_screen = TouchScreen(touch_queue, BUZZER_PIN, config["general"]["rotation"])

    dash_name = "main"
    while True:
        touch_areas = dash_manager.show_dashboard(dash_name)
        try:
            touch_coords = touch_queue.get(timeout=5)
        except queue.Empty:
            continue
        new_dash = dash_manager.resolve_touch(touch_coords)
        print(f"Switching to dashboard: {new_dash}")
        if new_dash is not None:
            dash_name = new_dash
