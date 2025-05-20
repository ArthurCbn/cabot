from pathlib import Path
from mutagen.flac import FLAC
from mutagen.aiff import AIFF
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TKEY
import random as rd
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page
from time import sleep
from .rip import extract_track_id

TUNEBAT_URL = "https://tunebat.com/Search?q="

PITCH_CLASS_TO_CAMELOT = {
    ("0", "0"): "5A",
    ("0", "1"): "8B",
    ("1", "0"): "12A",
    ("1", "1"): "3B",
    ("2", "0"): "7A",
    ("2", "1"): "10B",
    ("3", "0"): "2A",
    ("3", "1"): "5B",
    ("4", "0"): "9A",
    ("4", "1"): "12B",
    ("5", "0"): "4A",
    ("5", "1"): "7B",
    ("6", "0"): "11A",
    ("6", "1"): "2B",
    ("7", "0"): "6A",
    ("7", "1"): "9B",
    ("8", "0"): "1A",
    ("8", "1"): "11B",
    ("9", "0"): "8A",
    ("9", "1"): "11B",
    ("10", "0"): "3A",
    ("10", "1"): "6B",
    ("11", "0"): "10A",
    ("11", "1"): "1B",
}


def write_keys_in_aiff(songs: list[Path], id_to_key_dict: dict[str, str]) -> None :

    for song_path in songs :
        song_data = AIFF(song_path)
        song_id = extract_track_id(song_path)

        if song_id in id_to_key_dict :
            song_data.tags.add(TKEY(encoding=3, text=id_to_key_dict[song_id]))
        song_data.save()
    
    return


def write_keys_in_mp3(songs: list[Path], id_to_key_dict: dict[str, str]) -> None :

    for song_path in songs :
        song_data = MP3(song_path, ID3=ID3)
        song_id = extract_track_id(song_path)
        
        if song_id in id_to_key_dict :
            song_data.tags.add(TKEY(encoding=3, text=id_to_key_dict[song_id]))
        song_data.save()
    
    return


def scan_FLAC_folder_for_key_queries(folder: Path) -> dict[str, str] :
    
    queries = {}
    for track in folder.glob("*.flac") :
        track_data = FLAC(track)

        track_id = str(track_data["COMMENT"][0])
        title = str(track_data["TITLE"][0])
        artists = " ".join(track_data["ARTIST"])

        queries[track_id] = f"{title} {artists}".replace("'", " ") # Remove bad char
    
    return queries
        

def scrape_keys_from_tunebat(
        queries: dict[str, str],
        tunebat_url: str=TUNEBAT_URL) -> dict[str, str|None] :

    def _search_for_key_in_html(html: str, query: str) -> str|None :
        """
        The interesting html portion looks like this :

        <div>
            <div>Artists</div>
            <div>Song title</div>
        </div>
        <div>
            <div>
                <p>C Minor<\p>
                <p>Key</p>
            </div>
        </div>
        """

        soup = BeautifulSoup(html, "html.parser")
        
        if (p_key := soup.find('p', text="Key")) is None:
            return None
        key = p_key.find_previous_sibling('p').get_text()
        
        # If the p_key exists, then the whole structure exists
        outer_div = p_key.find_parent('div')
        outer_div = outer_div.find_parent('div')
        artists_title_parent_div = outer_div.find_previous_sibling('div')
        artists_title_divs = artists_title_parent_div.find_all('div')
        
        artists = artists_title_divs[0].get_text().lower()
        title = artists_title_divs[1].get_text().lower()

        # Check if at least one artist matches the searched track
        artists_list = artists.split(",")
        if all(a.strip() not in query.lower() for a in artists_list) :
            return None
        
        # Remove potential (feat. abc) substring
        title_with_no_feat = re.sub(r"\(*feat(\.)*\s*.*", "", title)
        if title_with_no_feat not in query.lower() :
            return None
        
        return key


    def _scrape_key_by_query(
            query: str,
            previous_query: str,
            page: Page,
            wait_s: float) -> str|None:
        
        # Fill the search field
        input_element = page.locator(f"input[value*='{previous_query}']")
        input_element.fill(query)
        
        # Click search button
        filled_input = page.locator(f"input[value*='{query}']")
        button = filled_input.locator(f"xpath=../../button")
        button.click()

        sleep(wait_s)

        html = page.content()
        key = _search_for_key_in_html(html, query)

        return key


    if len(queries) == 0 :
        return {}
    
    res = {}
    queries_stack = list(queries.items())

    # Launch Chromium browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
 
        # Go to the URL
        t_id, previous_query = queries_stack.pop(0)
        page.goto(tunebat_url + previous_query)

        # Wait for content to load
        page.wait_for_timeout(10000)

        # First key
        html = page.content()
        res[t_id] = _search_for_key_in_html(html, previous_query)

        while queries_stack :
            t_id, query = queries_stack.pop(0)

            # waitime = rd.random()*2.5 + 1.5 # between 1.5s and 4s TODO play around with the timing to not get blocked after ~10 searches
            waitime = 1.5

            key = _scrape_key_by_query(query,
                                       previous_query, 
                                       page,
                                       waitime)

            # Not found tracks are retried later, maximum 1 retry
            if (key is None) and (t_id not in res) :
                queries_stack.append((t_id, query))
            
            res[t_id] = key
            previous_query = query

        browser.close()
    
    return res


def convert_keys(keys: dict[str, str|None]) -> dict[str, str] :

    for id, key in keys.copy().items() :
        
        if key is None :
            keys.pop(id)
        else :
            keys[id] = key.replace('♭', 'b').replace("Major", "").replace("Minor", "m").strip()
    
    return keys