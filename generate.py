#!/usr/bin/env python3
import random
import sys
import os.path
import configparser
import datetime

import requests
import jinja2


URL_STREAMS = "https://api.twitch.tv/helix/streams"
URL_USERS = "https://api.twitch.tv/helix/users"
URL_GAMES = "https://api.twitch.tv/helix/games"


if len(sys.argv) != 3:
    print("Usage: {} <config dir> <output file>".format(sys.argv[0]))
    exit(1)

config_dir = sys.argv[1]
output_path = sys.argv[2]

with open(os.path.join(config_dir, "streamers.txt")) as streamers_file:
    streamer_slugs = [
        slug.strip().lower() for slug in streamers_file.readlines()]

with open(os.path.join(config_dir, "config.ini")) as config_file:
    config = configparser.ConfigParser()
    config.read_file(config_file)
    site_name = config["MAIN"]["name"]
    token = config["MAIN"]["token"]

session = requests.Session()
session.headers = {"Client-ID": token}

users_resp = session.get(URL_USERS, params={"login": streamer_slugs})
users_result = users_resp.json()
try:
    users = {user["id"]: user for user in users_result["data"]}
except KeyError:
    print(users_result)
    exit(1)

streams_resp = session.get(
    URL_STREAMS, params={"user_login": streamer_slugs, "first": 100})
streams_result = streams_resp.json()
try:
    streams = streams_result["data"]
except KeyError:
    print(streams_result)
    exit(1)
for stream in streams:
    users[stream["user_id"]]["stream"] = stream

game_ids = set()
for stream in streams:
    game_ids.add(stream["game_id"])
if game_ids:
    games_resp = session.get(URL_GAMES, params={"id": game_ids})
    games_result = games_resp.json()
    try:
        games = {game["id"]: game for game in games_result["data"]}
    except KeyError:
        print(games_result)
        exit(1)
    for stream in streams:
        if stream["game_id"] != "0":
            stream["game"] = games[stream["game_id"]]

users_list = list(users.values())
random.shuffle(users_list)
users_list.sort(
    reverse=True,
    key=lambda u: u.get("stream", {}).get("viewer_count", -1))

timestamp = datetime.datetime.now()

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("."),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True
)
template = env.get_template("template.html")
page = template.render(
    site_name=site_name, streamers=users_list, timestamp=timestamp)
with open(output_path, "w") as page_file:
    page_file.write(page)
