import requests
from bs4 import BeautifulSoup
from alive_progress import alive_bar, alive_it
import os
import csv
from datetime import datetime, timedelta
import re
from pathlib import Path
import json

from yaml import dump_all

download_folder = "downloads"

os.chdir(os.path.dirname(os.path.realpath(__file__)))


def make_url(page_no : int = 1) -> str:
    return f"https://webbtelescope.org/resource-gallery/images?page={page_no}"

def get_num_images() -> int:
    html = requests.get(make_url()).text
    soup = BeautifulSoup(html, "html.parser")

    txt = soup.select(".filter-bar__before-results")[0].select("strong")[0].text
    return int(txt.replace("(","").replace(")","").replace("total","").strip())

def get_image_tiles(html : str):
    soup = BeautifulSoup(html, "html.parser")
    return soup.select(".col-sm-4")

def get_image_page_uri(image_tile) -> str:
    return image_tile.select("a.link-wrap")[0]["href"].split("?")[0]

def get_download_links(url : str) -> dict[str,list[str]]:
    html = (r:=requests.get(url)).text
    # try:
    soup = BeautifulSoup(html, "html.parser")
    name = clean_file_name(soup.select(".section-header__title")[0].text.strip())
    links = soup.select(".media-library-links-list")[0].select("a")
    return {
        name : [
            ("https:"+ link["href"], [substr for substr in link.text.split(",") if " X " in substr][0].lower().strip() if "X" in link.text else None)
        for link in links]
    }
    # except Exception as e:
    #     print("Exception:", e)
    #     print(r.status_code)
    #     # print(r.text)
    #     input()

def clean_file_name(name : str) -> str:
    return name.replace(")","").replace("(","- ").replace(": "," - ").replace("/","-")

def cache_download_links(links : dict):
    with open("download_links.json", "w",encoding="utf-8") as f:
        f.write(json.dumps(links))

def load_download_links() -> dict:
    with open("download_links.json", "r",encoding="utf-8") as f:
        return json.loads(f.read())

def scrape_download_links() -> dict[str,list[str]]:
    n = get_num_images()
    page_no = 0
    download_links : dict[str,list[str]] = {}
    with alive_bar(n, dual_line=True, title="Scraping Download Links") as bar:
        ## Scrape all download links ##
        while True:
            page_no += 1
            bar.text = f" > Scraping Page #{page_no}"
            html = requests.get(make_url(page_no=page_no)).text
            num_results = len(image_tiles:=get_image_tiles(html=html))
            count = 0
            for image_tile in image_tiles:
                bar.text = f" > Scraping Page #{page_no} - Image #{count}"
                url = f"https://webbtelescope.org{get_image_page_uri(image_tile=image_tile)}"
                download_links.update(get_download_links(url))
                bar()
                count+=1
                
            cache_download_links(download_links)
            
            if num_results != 15:
                break
    return download_links

def download_files(links : dict = None):
    if not links:
        links = load_download_links()
        links = {clean_file_name(name) : links[name] for name in links}
        cache_download_links(links)
    n = sum([len(links[name]) for name in links])
    with alive_bar(n, dual_line=True, title="Downloading Files") as bar:
        for name in links:
            count = 0
            for link, size in links[name]:
                count += 1
                bar.text = f" > Downloading File #{count} | {name}"
                try:
                    r = requests.get(link)
                    extension = link.split(".")[-1]
                    Path(f"{download_folder}/{extension}").mkdir(parents=True, exist_ok=True)
                    open(f"{download_folder}/{extension}/{name} - {size}.{extension}", "wb").write(r.content)
                except Exception as e:
                    print(f"download failed for {name}, {size}, {link}")
                    print(e)
                bar()

scrape_download_links()

download_files()
