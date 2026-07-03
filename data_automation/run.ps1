$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$HadoopHome = Join-Path $ProjectRoot ".hadoop"

if (-not (Test-Path $Python)) {
    python -m venv (Join-Path $ProjectRoot ".venv")
}

if (Test-Path (Join-Path $HadoopHome "bin\winutils.exe")) {
    $env:HADOOP_HOME = $HadoopHome
    $env:hadoop_home_dir = $HadoopHome
    $env:PATH = "$HadoopHome\bin;$env:PATH"
}

$env:PYSPARK_PYTHON = $Python

Write-Host "Generating sample spreadsheets..."
& $Python .\src\generate_sample_data.py

Write-Host "Running Spark pipeline..."
& $Python .\src\pipeline.py --input .\input --output .\output

Write-Host "Validating outputs..."
& $Python .\src\validate_outputs.py --output .\output

Write-Host "GeriCare data automation finished."
