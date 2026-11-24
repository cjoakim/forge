"""
Usage:
  Fetching the data from the Football Data API:
    uv run main.py football_data_areas
    uv run main.py football_data_areas 2072
    uv run main.py football_data_competitions PL
    uv run main.py football_data_teams_in_league PL
    uv run main.py football_data_standings PL
    uv run main.py football_data_matches PL
    uv run main.py football_data_persons PL
  Exploring the data, cast to csv:
    uv run main.py football_data_parse_standings pl
    uv run main.py football_data_parse_matches pl
    uv run main.py football_data_parse_teams pl
    uv run main.py football_data_enhance_stadiums pl
  Transform and Merge the data for AI Search and/or Cosmos DB:
    uv run main.py transform_merge_db_data
  Other transformations:
    uv run main.py compute_map_center ../data/uk_football/stadiums_pl.json
    uv run main.py gen_google_map ../data/uk_football/stadiums_pl.json
"""


from doctest import DocTest
import json
import sys
import time
import os
import traceback
import uuid

from dotenv import load_dotenv

import httpx
import jinja2


def football_data_areas(code):
    if code is None:
        url = f"https://api.football-data.org/v4/areas"
    else:
        url = f"https://api.football-data.org/v4/areas/{code}"

    response = invoke_get_football_data(url, f"tmp/areas_{code}.json")
    return response


def football_data_competitions(league):
    if league is None:
        url = f"https://api.football-data.org/v4/competitions"
    else:
        url = f"https://api.football-data.org/v4/competitions/{league}"

    response = invoke_get_football_data(url, f"tmp/competitions_{league}.json")
    return response


def football_data_standings(league):
    url = f"https://api.football-data.org/v4/competitions/{league}/standings"

    response = invoke_get_football_data(url, f"tmp/standings_{league}.json")
    return response


def football_data_teams_in_league(league):
    url = f"https://api.football-data.org/v4/competitions/{league}/teams"

    response = invoke_get_football_data(url, f"tmp/teams_{league}.json")
    return response


def football_data_matches(league):
    url = f"https://api.football-data.org/v4/competitions/{league}/matches"
    response = invoke_get_football_data(url, f"tmp/matches_{league}.json")
    return response


def football_data_persons(league):
    ids = dict()
    teams_data = read_json(f"tmp/teams_{league}.json")
    for team in teams_data["teams"]:
        id = team["id"]
        name = team["name"]
        if "coach" in team.keys():
            coach = team["coach"]
            if "id" in coach.keys():
                if coach["id"] is not None:
                    ids[coach["id"]] = "coach"
        if "squad" in team.keys():
            for player in team["squad"]:
                if "id" in player.keys():
                    if player["id"] is not None:
                        ids[player["id"]] = "player"
        if "staff" in team.keys():
            for staff in team["staff"]:
                if "id" in staff.keys():
                    if staff["id"] is not None:
                        ids[staff["id"]] = "staff"
    write_json(ids, f"tmp/persons_ids_{league}.json")

    # The API has rate limiting; is apt to return HTTP status code 429 errors.
    initial_delay, loop_delay = 90.0, 8.0
    print(f"persons: {len(ids)} ids to process")
    print(f"persons: {initial_delay} seconds initial delay...")

    if True:
        ids_to_process = list()
        for id in sorted(ids.keys()):
            outfile = f"tmp/persons_{id}.json"
            if file_exists(outfile):
                print(f"file exists: {outfile}")
            else:
                ids_to_process.append(int(id))
        num_to_process = len(ids_to_process)
        print(f"ids_to_process: {num_to_process} ids to process")
        print(ids_to_process)

        for idx, id in enumerate(sorted(ids_to_process)):
            outfile = f"tmp/persons_{id}.json"
            # Registered clients are allowed for 10 requests/minute in the free plan
            time.sleep(loop_delay)
            url = f"https://api.football-data.org/v4/persons/{id}"
            print(
                f"[{idx + 1} of {num_to_process}] - waiting {loop_delay} seconds to invoke {url} ..."
            )
            response = invoke_get_football_data(url, f"tmp/persons_{id}.json")
            print(f"url: {url} --> {response.status_code}")
            if response.status_code == 200:
                jdata = json.loads(response.text)
                write_json(jdata, f"tmp/persons_{id}.json")


def football_data_parse_standings(league):
    standings_data = read_json(f"tmp/standings_{league}.json")
    for standing in standings_data["standings"]:
        for team in standing["table"]:
            position = team["position"]
            team_name = team["team"]["shortName"]
            points = team["points"]
            played = team["playedGames"]
            won = team["won"]
            draw = team["draw"]
            lost = team["lost"]
            goals_for = team["goalsFor"]
            goals_against = team["goalsAgainst"]
            goal_difference = team["goalDifference"]
            print(
                f"{position}|{team_name}|{points}pts|{played}p|{won}w|{draw}d|{lost}l|{goals_for}gf|{goals_against}ga|{goal_difference}gd"
            )


def football_data_parse_matches(league):
    matches_data = read_json(f"tmp/matches_{league}.json")
    lpool, lpool_count = "Liverpool", 0
    for match in matches_data["matches"]:
        hteam = match["homeTeam"]["shortName"]
        ateam = match["awayTeam"]["shortName"]
        mdate = match["utcDate"].split("T")[0]
        status = match["status"]
        winner, duration, score, home_score, away_score = "", "", "", "", ""

        if status == "FINISHED":
            winner = match["score"]["winner"].lower()
            duration = match["score"]["duration"].lower()
            home_score = match["score"]["fullTime"]["home"]
            away_score = match["score"]["fullTime"]["away"]
            score = f"{home_score} - {away_score}"

        print(f"{mdate}, {ateam} at {hteam}, {status} {winner} {score} {duration}")

        if hteam == lpool:
            lpool_count = lpool_count + 1
        if ateam == lpool:
            lpool_count = lpool_count + 1
    print(f"{lpool} plays {lpool_count} matches")


def football_data_parse_teams(league):
    data = read_json(f"tmp/teams_{league}.json".lower())
    teams = data["teams"]
    for team in teams:
        name = team["name"]
        id = team["id"]
        short_name = team["shortName"]
        tla = team["tla"]
        crest = team["crest"]
        address = team["address"]
        website = team["website"]
        founded = team["founded"]
        venue = team["venue"]
        print(f"{id}|{name}|{short_name}|{tla}|{founded}|{venue}|{address}|{website}")


def football_data_enhance_stadiums(league):
    data = read_json(f"tmp/teams_{league}.json".lower())
    teams = data["teams"]
    for team in teams:
        name = team["name"]
        id = team["id"]
        short_name = team["shortName"]
        tla = team["tla"]
        crest = team["crest"]


def gen_google_map(infile):
    stadiums = read_json(infile)
    stadiums_json = json.dumps(
        [
            {
                "team_name": stadium["team_name"],
                "city": stadium["team_city"],
                "stadium_name": stadium["team_stadium_name"],
                "lat": stadium["team_stadium_latitude"],
                "lng": stadium["team_stadium_longitude"],
            }
            for stadium in stadiums
        ]
    )
    write_json(stadiums_json, f"tmp/stadiums.json")

    t = get_template("templates", "gmap.html")
    values = {
        "GOOGLE_MAPS_KEY": os.getenv("GOOGLE_MAPS_KEY"),
        "center_latitude": "52.282686",
        "center_longitude": "-1.520889",
        "zoom_level": "7",
        "stadiums_json": stadiums_json,
    }
    html = render(t, values)
    with open("tmp/epl_map.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"file written: tmp/epl_map.html")


def compute_map_center(infile):
    stadiums = read_json(infile)
    latitudes, longitudes = [], []
    for stadium in stadiums:
        lat = stadium["team_stadium_latitude"]
        lng = stadium["team_stadium_longitude"]
        latitudes.append(float(lat))
        longitudes.append(float(lng))
        print(f"{lat}, {lng}")

    center_latitude = sum(latitudes) / len(latitudes)
    center_longitude = sum(longitudes) / len(longitudes)
    print(f"center_latitude: {center_latitude}, center_longitude: {center_longitude}")


def transform_merge_db_data():
    """
    Read the various data files and produce a single transformed/merged file that
    can be loaded into the AI Search 'epl' index or a Cosmos DB container.
    """
    print("transform_merge_db_data")
    merged_documents = []
    locations = {}
    player_dict = {}  # key is player name, value is lc_team

    # stadiums
    infile = "../data/epl_v0/stadiums.json"
    stadiums_v1 = read_json(infile)
    stadiums_v2 = []
    for raw in stadiums_v1:
        doc = {}
        doc["id"] = str(uuid.uuid4())
        doc["pk"] = "stadium"
        doc["doctype"] = "stadium"
        doc["team"] = raw["team"]
        doc["city"] = raw["city"]
        doc["stadium"] = raw["stadium"]
        doc["latitude"] = raw["latitude"]
        doc["longitude"] = raw["longitude"]
        doc["location"] = raw["location"]
        locations[doc["team"].lower()] = doc["location"]  # collect the locations for later use
        stadiums_v2.append(doc)
        merged_documents.append(doc)

    write_json(stadiums_v2, "../data/epl/stadiums_v2.json")
    write_json(locations, "../data/epl/locations_v2.json")
    print(f"stadiums count: {len(stadiums_v2)}")

    # matches/schedule
    infile = "../data/epl_v0/matches.json"
    delete_keys = "id|area|season|status|group|competition|lastUpdated|score|odds|referees".split(
        "|"
    )
    matches_v2, team_names = [], {}
    matches = read_json(infile)
    for doc in matches:
        for key in delete_keys:
            if key in doc.keys():
                del doc[key]
        lc_home_team = doc["homeTeam"]["shortName"].lower()
        lc_away_team = doc["awayTeam"]["shortName"].lower()
        team_names[lc_home_team] = doc["homeTeam"]["shortName"]
        team_names[lc_away_team] = doc["awayTeam"]["shortName"]

        doc["id"] = str(uuid.uuid4())
        doc["pk"] = "match"
        doc["doctype"] = "match"
        doc["lc_home_team"] = lc_home_team
        doc["lc_away_team"] = lc_away_team
        if "stage" in doc.keys():
            doc["stage"] = doc["stage"].lower()
        doc["date"] = doc["utcDate"].split("T")[0]
        doc["time"] = doc["utcDate"].split("T")[1][:5]
        if lc_home_team in locations.keys():
            doc["location"] = locations[lc_home_team]
        else:
            print(f"location_not_found for {lc_home_team}")

        matches_v2.append(doc)
        merged_documents.append(doc)
    write_json(matches_v2, "../data/epl/matches_v2.json")
    print(f"matches count: {len(matches_v2)}")

    # teams
    infile = "../data/epl_v0/teams.json"
    teams = read_json(infile)
    teams_v2 = []
    delete_keys = "area|runningCompetitions|coach|staff|lastUpdated".split("|")
    for doc in teams:
        lc_team = doc["shortName"].lower()
        doc["id"] = str(uuid.uuid4())
        doc["pk"] = "team"
        doc["doctype"] = "team"
        doc["lc_team"] = lc_team
        for key in delete_keys:
            if key in doc.keys():
                del doc[key]
        if lc_team in locations.keys():
            doc["location"] = locations[lc_team]
        else:
            print(f"location_not_found for {lc_team}")
        teams_v2.append(doc)
        merged_documents.append(doc)

        if "squad" in doc.keys():
            for player in doc["squad"]:
                if "name" in player.keys():
                    player_dict[player["name"].strip()] = lc_team
    write_json(teams_v2, "../data/epl/teams_v2.json")
    print(f"teams count: {len(teams_v2)}")
    write_json(player_dict, "../data/epl/player_dict_v2.json")
    print(f"player_dict count: {len(player_dict)}")

    # players
    infile = "../data/epl_v0/players.json"
    players_v1 = read_json(infile)
    players_v2 = []
    for idx, player in enumerate(players_v1):
        if "name" in player.keys():
            pname = player["name"].strip()
            epl_team = "unknown"
            if pname in player_dict.keys():
                epl_team = player_dict[pname]
            else:
                print(f"player_not_found in player_dict: {pname}")
            player["id"] = str(uuid.uuid4())
            player["pk"] = "player"
            player["doctype"] = "player"
            player["lc_team"] = epl_team
            players_v2.append(player)
            merged_documents.append(player)
        else:
            print(f"player data not in players.json idx {idx}")
    write_json(players_v2, "../data/epl/players_v2.json")
    print(f"players count: {len(players_v2)}")

    write_json(merged_documents, "../data/epl/merged_documents_v2.json")
    print(f"merged_documents count: {len(merged_documents)}")


def invoke_get_football_data(url, outfile):
    headers = {"X-Auth-Token": os.getenv("FOOTBALL_DATA_API_TOKEN")}
    print(f"invoke_get_football_data: url: {url}")
    response = httpx.get(url, headers=headers)
    print(response.status_code)
    jdata = json.loads(response.text)
    write_json(jdata, outfile)
    return response


def write_json(data, outfile):
    with open(outfile.lower(), "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=4))
        f.write("\n")
        print(f"file written: {outfile.lower()}")


def read_json(infile):
    with open(infile.lower(), "r", encoding="utf-8") as f:
        return json.load(f)
    return None


def file_exists(filename):
    return os.path.exists(filename.lower())


def list_files_in_directory(directory):
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]


def get_template(root_dir: str, template_file: str):
    return _get_jinja2_env(root_dir).get_template(template_file)


def render(template, values: dict) -> str:
    """Render the given template object with the given dict of values."""
    return template.render(values)


def _get_jinja2_env(root_dir: str):
    """
    Private method to return a jinja2 Environment object for the
    given root_dir.
    """
    return jinja2.Environment(loader=jinja2.FileSystemLoader(root_dir), autoescape=False)


def print_options(msg: str | None = None) -> None:
    if msg is not None:
        print(msg)
    print(__doc__)


if __name__ == "__main__":
    try:
        load_dotenv(override=True)
        func = sys.argv[1].lower()
        if func == "football_data_competitions":
            league = sys.argv[2]
            football_data_competitions(league)
        elif func == "football_data_areas":
            code = None
            if len(sys.argv) > 2:
                code = sys.argv[2]
            football_data_areas(code)
        elif func == "football_data_standings":
            league = sys.argv[2]
            football_data_standings(league)
        elif func == "football_data_teams_in_league":
            league = sys.argv[2]
            football_data_teams_in_league(league)
        elif func == "football_data_matches":
            league = sys.argv[2]
            football_data_matches(league)
        elif func == "football_data_persons":
            league = sys.argv[2]
            football_data_persons(league)

        elif func == "football_data_parse_standings":
            league = sys.argv[2]
            football_data_parse_standings(league)
        elif func == "football_data_parse_matches":
            league = sys.argv[2]
            football_data_parse_matches(league)
        elif func == "football_data_parse_teams":
            league = sys.argv[2]
            football_data_parse_teams(league)
        elif func == "football_data_enhance_stadiums":
            league = sys.argv[2]
            football_data_enhance_stadiums(league)
        elif func == "gen_google_map":
            infile = sys.argv[2]
            gen_google_map(infile)
        elif func == "compute_map_center":
            infile = sys.argv[2]
            compute_map_center(infile)
        elif func == "transform_merge_db_data":
            transform_merge_db_data()
        else:
            print_options("Error: invalid function: {}".format(func))
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
