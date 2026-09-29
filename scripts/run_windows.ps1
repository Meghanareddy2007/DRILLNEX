Set-Location (Join-Path $PSScriptRoot '..')
if (!(Test-Path '.venv\Scripts\python.exe')) { py -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Location backend
& ..\.venv\Scripts\python.exe app.py
