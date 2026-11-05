param([switch]$Classroom)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskTemp = Join-Path $PSScriptRoot '.venv-tmp'
New-Item -ItemType Directory -Force -Path $taskTemp | Out-Null
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
$taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    python -m venv --without-pip .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& $taskPython -c "import streamlit, numpy, pandas, plotly" 2>$null
if ($LASTEXITCODE -ne 0) {
    python -m pip --python $taskPython install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the app dependencies.' }
}
& $taskPython -c "import storage; storage.initialize(); storage.admin_password(); print('Admin password file:', storage.data_dir() / 'admin-password.txt')"
if ($LASTEXITCODE -ne 0) { throw 'Could not initialize the app. See README.md.' }
if ($Classroom) {
    & $taskPython -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
} else {
    & $taskPython -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
}
