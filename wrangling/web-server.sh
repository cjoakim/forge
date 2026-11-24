#!/bin/bash

# Display the Google Map for the England and EPL Football Teams
# via a localhost http server.  Be sure to add YOUR Google Map Key
# to file tmp/epl_map.html.

echo 'visit http://localhost:8080/tmp/epl_map.html with your web browser'

echo "starting the localhost http server on port 8080 ..."
python3 -m http.server 8080
