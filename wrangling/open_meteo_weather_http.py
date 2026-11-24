import json

# This script explores the Open-Meteo API using HTTP requests
# for the potential use as an Agentic Tool.

import requests

WEATHER_CODES = {
    "0": "Clear sky",
    "1": "Mainly clear",
    "2": "Partly cloudy",
    "3": "Overcast",
    "45": "Fog",
    "48": "Depositing rime fog",
    "51": "Drizzle: light intensity",
    "53": "Drizzle: moderate intensity",
    "55": "Drizzle: dense intensity",
    "56": "Freezing drizzle: light intensity",
    "57": "Freezing drizzle: dense intensity",
    "61": "Rain: slight intensity",
    "63": "Rain: moderate intensity",
    "65": "Rain: heavy intensity",
    "66": "Freezing rain: light intensity",
    "67": "Freezing rain: heavy intensity",
    "71": "Snow fall: slight intensity",
    "73": "Snow fall: moderate intensity",
    "75": "Snow fall: heavy intensity",
    "77": "Snow grains",
    "80": "Rain showers: slight intensity",
    "81": "Rain showers: moderate intensity",
    "82": "Rain showers: violent intensity",
    "85": "Snow showers: slight intensity",
    "86": "Snow showers: heavy intensity",
    "95": "Thunderstorm: slight or moderate",
    "96": "Thunderstorm with slight hail",
    "99": "Thunderstorm with heavy hail",
}


def write_json(data, outfile):
    with open(outfile.lower(), "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=4))
        f.write("\n")
        print(f"file written: {outfile.lower()}")


if True:
    lat, lon = 51.5549, -0.1084  # Emirates Stadium, London, Arsenal
    lat, lon = 35.499302, -80.848686  # Davidson, NC, USA

    # url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,rain,weather_code,surface_pressure"
    # url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weather_code&hourly=temperature_2m,rain,weather_code,surface_pressure,cloud_cover&forecast_days=1"
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=weather_code&hourly=temperature_2m,rain,weather_code,surface_pressure,cloud_cover,precipitation_probability,relative_humidity_2m,wind_speed_10m,wind_direction_10m&timezone=GMT&forecast_days=16"

    response = requests.get(url)
    print(response)
    print(response.text)
    obj = json.loads(response.text)
    write_json(obj, "tmp/open_meteo_weather_http.json")

    hours = len(obj["hourly"]["time"])
    print(f"Hours: {hours}")
    for n in range(hours):
        time = obj["hourly"]["time"][n].replace("T", " ")
        tempc = obj["hourly"]["temperature_2m"][n]
        tempf = tempc * 9 / 5 + 32
        code = str(obj["hourly"]["weather_code"][n])
        desc = "?"
        if code in WEATHER_CODES.keys():
            desc = WEATHER_CODES[code]
        print(f"Time: {time}, {tempf}F, {tempc}C, {desc}")
