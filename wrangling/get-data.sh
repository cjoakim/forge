#!/bin/bash

# This script fetches the data from the Football Data API
# and saves it to the tmp directory for further processing.
#
# Per the https://api.football-data.org/v4/ API:
# - The English Premier League is ID: 2021, code PL
# - The current season ID is 2502
# - England is Area ID: 2072

mkdir -p tmp
rm tmp/*.*

uv run main.py football_data_competitions PL

uv run main.py football_data_areas
uv run main.py football_data_areas 2072

uv run main.py football_data_standings PL 2502

uv run main.py football_data_teams_in_league PL

uv run main.py football_data_matches PL

uv run main.py football_data_persons pl

echo 'done'
