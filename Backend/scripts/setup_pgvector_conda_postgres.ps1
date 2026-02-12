[CmdletBinding()]
param(
  [string]$EnvName = "graphbit-pgvector",
  [string]$DataDir = "",
  [int]$Port = 5434,
  [string]$EnvFile = "",
  [switch]$ForceReinit
)

$ErrorActionPreference = 'Stop'

if (-not $PSScriptRoot) {
  throw "PSScriptRoot is not set. Run this script with: powershell -File <path>"
}

if (-not $DataDir) {
  $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  $DataDir = Join-Path (Join-Path $projectRoot ".conda_pg") "data"
}

if (-not $EnvFile) {
  if (-not $projectRoot) {
    $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  }
  $EnvFile = Join-Path $projectRoot ".env"
}

function Write-Info([string]$msg) { Write-Host "[conda-pgvector] $msg" }

function Get-EnvMap([string]$path) {
  if (-not (Test-Path $path)) { throw "Env file not found: $path" }
  $map = @{}
  Get-Content $path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line) { return }
    if ($line.StartsWith('#')) { return }
    $idx = $line.IndexOf('=')
    if ($idx -lt 1) { return }
    $k = $line.Substring(0, $idx).Trim()
    $v = $line.Substring($idx + 1).Trim()
    $map[$k] = $v
  }
  return $map
}

function Require-Command([string]$name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) { throw "$name not found on PATH" }
  return $cmd.Source
}

function Invoke-CondaRun([string]$envName, [string[]]$args, [switch]$AllowNonZero) {
  & conda run -n $envName @args | Write-Host
  if (-not $AllowNonZero -and $LASTEXITCODE -ne 0) {
    throw "conda run failed (exit $LASTEXITCODE): $($args -join ' ')"
  }
}

function Wait-ForPostgres([string]$envName, [int]$port, [int]$timeoutSeconds = 30) {
  $deadline = (Get-Date).AddSeconds($timeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    & conda run -n $envName pg_isready -h 127.0.0.1 -p $port | Out-Null
    if ($LASTEXITCODE -eq 0) { return }
    Start-Sleep -Milliseconds 500
  }
  throw "Postgres did not become ready on port $port within ${timeoutSeconds}s"
}

$conda = Require-Command "conda"
Write-Info "Using conda: $conda"

# Make sure conda-forge is available and env exists
$envList = & conda env list
if ($envList -notmatch "^$EnvName\s") {
  Write-Info "Creating conda env '$EnvName' with postgresql=18 + pgvector"
  & conda create -y -n $EnvName -c conda-forge postgresql=18 pgvector | Write-Host
} else {
  Write-Info "Conda env '$EnvName' already exists"
}

$envMap = Get-EnvMap $EnvFile
$password = if ($envMap.ContainsKey('POSTGRES_PASSWORD')) { $envMap['POSTGRES_PASSWORD'] } else { "admin" }
$user = if ($envMap.ContainsKey('POSTGRES_USER')) { $envMap['POSTGRES_USER'] } else { "postgres" }
$db = if ($envMap.ContainsKey('POSTGRES_DB')) { $envMap['POSTGRES_DB'] } else { "postgres" }

if (-not $projectRoot) {
  $projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$pwFileDir = Join-Path $projectRoot ".conda_pg"
New-Item -ItemType Directory -Force -Path $pwFileDir | Out-Null
$pwFile = Join-Path $pwFileDir "pwfile.txt"
Set-Content -Path $pwFile -Value $password -NoNewline

$DataDir = (Resolve-Path (New-Item -ItemType Directory -Force -Path $DataDir)).Path
Write-Info "PGDATA: $DataDir"
Write-Info "Port: $Port"

if ($ForceReinit -and (Test-Path (Join-Path $DataDir "PG_VERSION"))) {
  Write-Info "ForceReinit set; deleting existing data dir"
  Remove-Item -Recurse -Force $DataDir
  New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
}

# Initialize if needed
if (-not (Test-Path (Join-Path $DataDir "PG_VERSION"))) {
  Write-Info "Initializing database cluster"
  Invoke-CondaRun -envName $EnvName -args @('initdb','-D',$DataDir,'-U',$user,'-A','scram-sha-256','--pwfile',$pwFile)

  # Configure port + listen
  $conf = Join-Path $DataDir "postgresql.conf"
  Add-Content $conf "`n# Graphbit conda pgvector instance`nport = $Port`nlisten_addresses = '127.0.0.1'`n"
}

# Start server
Write-Info "Starting Postgres (if not already running)"
$logFile = Join-Path $DataDir "postgres.log"

& conda run -n $EnvName pg_ctl -D $DataDir status | Out-Null
if ($LASTEXITCODE -eq 0) {
  Write-Info "Postgres already running"
} else {
  Invoke-CondaRun -envName $EnvName -args @('pg_ctl','-D',$DataDir,'-l',$logFile,'-o',"-p $Port -h 127.0.0.1",'-w','start')
}

Write-Info "Waiting for readiness"
Wait-ForPostgres -envName $EnvName -port $Port -timeoutSeconds 45

# Ensure DB exists (createdb errors if it exists; ignore)
Write-Info "Ensuring database '$db' exists"
try {
  Invoke-CondaRun -envName $EnvName -args @('createdb','-h','127.0.0.1','-p',"$Port",'-U',$user,$db)
} catch {
  # ignore
}

# Enable extension
Write-Info "Enabling pgvector extension in '$db'"
$env:PGPASSWORD = $password
Invoke-CondaRun -envName $EnvName -args @('psql','-h','127.0.0.1','-p',"$Port",'-U',$user,'-d',$db,'-v','ON_ERROR_STOP=1','-c','CREATE EXTENSION IF NOT EXISTS vector;')
Invoke-CondaRun -envName $EnvName -args @('psql','-h','127.0.0.1','-p',"$Port",'-U',$user,'-d',$db,'-v','ON_ERROR_STOP=1','-c',"SELECT extname, extversion FROM pg_extension WHERE extname='vector';")

Write-Info "Smoke test"
Invoke-CondaRun -envName $EnvName -args @('psql','-h','127.0.0.1','-p',"$Port",'-U',$user,'-d',$db,'-v','ON_ERROR_STOP=1','-c',"CREATE TEMP TABLE _pgvector_smoketest(id int, embedding vector(3)); INSERT INTO _pgvector_smoketest VALUES (1, '[1,2,3]'); SELECT * FROM _pgvector_smoketest;")

Write-Info "Done. Connection string: postgresql://${user}:${password}@localhost:${Port}/${db}"
Write-Info "Stop with: conda run -n $EnvName pg_ctl -D \"$DataDir\" stop"
