#!/usr/bin/env python3

import io
import time
import asyncio

import yaml
import aiohttp
import digitalio
import board

from PIL import Image, ImageDraw, ImageFont

from display import Display

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
        self.disp = disp

    def find_dashboard(self, dash_name):
        for dashboard in self.dashboards:
            if dashboard["id"] == dash_name:
                return dashboard
        raise ValueError(f"Dashboard not found: {dash_name}")

    def show_dashboard(self, dash_name):
        dashboard = self.find_dashboard(dash_name)
        urls = []
        for tile in dashboard["tiles"]:
            urls.append({
                "id": tile["id"],
                "url": tile["url"]
            })
        data = asyncio.run(fetch_urls(urls, config['general']['grafana_token']))

        dashboard_image = Image.new("RGB", (self.disp.d_width, self.disp.d_height), "#FFF")
        for tile in dashboard["tiles"]:
            try:
                image = Image.open(io.BytesIO(data[tile["id"]]["content"]))
                dashboard_image.paste(image, tile.get("placement", (0,0)))
            except Exception as ex:
                print(f"ERROR: {ex}")
                # Never mind, move on...

        self.disp.display_image(dashboard_image)

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

    while True:
        dash_manager.show_dashboard("main")
        time.sleep(5)
