# This script executes the complete set of unit tests,
# with code coverage reporting.

Write-Host "========== Activating the virtual environment =========="
. .\.venv\Scripts\Activate.ps1
python --version

if (Test-Path htmlcov) { Remove-Item -Recurse -Force htmlcov }

Write-Host "========== Executing unit tests with code coverage =========="
pytest -v --cov=src/ --cov-report html tests/

Write-Host "========== Running pylint =========="
# PowerShell doesn't expand wildcards for native commands, so expand *.py here
uv run pylint (Get-ChildItem -Name *.py) src
