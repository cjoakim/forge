# Display the Google Map for the England and EPL Football Teams
# via a localhost http server.  Be sure to add YOUR Google Map Key
# to file tmp\epl_map.html.
#
# On Windows the Python launcher is 'python' rather than 'python3'.

Write-Host 'visit http://localhost:8080/tmp/epl_map.html with your web browser'

Write-Host "starting the localhost http server on port 8080 ..."
python -m http.server 8080
