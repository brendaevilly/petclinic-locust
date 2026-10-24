param(
    [int]$Warmup = 60,
    [int]$Duration = 360,
    [int]$Repeats = 10,
    [string]$HostUrl = "http://localhost:8080"
)

Set-Location (Split-Path $PSScriptRoot -Parent)
python -m pip install -r requirements-loadtest.txt
python scripts/run_experiments.py --host $HostUrl --warmup $Warmup --duration $Duration --repeats $Repeats
python scripts/analyze_results.py
