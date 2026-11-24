# wrangling/web directory 

This directory contains a primitive HTML file containing a Google Map
of England with the location of the EPL teams.

It was used to create file **docs/img/epl-google-map.png** in this repo.

Mofify the HTML file (epl_map.html) at line 83 with **your** Google Map key
if you'd like to reproduce the map.

```
        key: "... your Google Maps API key ..."
```

You can start a simple python web server with this command:
```
python3 -m http.server 8080
```

Then visit http://localhost:8080/web/epl_map.html with your web browser
to see the Google Map.
