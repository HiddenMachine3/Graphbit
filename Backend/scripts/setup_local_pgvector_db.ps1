[CmdletBinding()]
param(
  [string]$CondaEnvName = "graphbit-pgvector-db",
  [int]$Port = 5434,
  [string]$DataDir = "",
  [string]$LogFile = "",
  [string]$DbName = "postgres",
  [string]$DbUser = "postgres",
  [string]$DbPassword = "admin"
)

$ErrorActionPreference = 'Stop'

if (-not $DataDir) {
  $baseDir = Join-Path (Join-Path $PSScriptRoot "..") ".local_pgvector_db"
  $DataDir = Join-Path $baseDir "data"
}

if (-not $LogFile) {
  $baseDir = Join-Path (Join-Path $PSScriptRoot "..") ".local_pgvector_db"
  $LogFile = Join-Path $baseDir "postgres.log"
}

function Write-Info([string]$msg) { Write-Host "[local-pgvector-db] $msg" }

function Assert-Command([string]$name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Required command not found on PATH: $name"
  }
}

function Get-CondaPrefix([string]$envName) {
  $json = conda env list --json | ConvertFrom-Json
  if (-not $json.envs) { throw "Could not read conda env list (--json)" }
  $match = $json.envs | Where-Object { (Split-Path $_ -Leaf) -ieq $envName } | Select-Object -First 1
  if (-not $match) { throw "Conda env '$envName' not found in conda env list" }
  return [string]$match
}

function Ensure-EnvExists([string]$envName) {
  $envList = conda env list
  if ($envList -match "^$([regex]::Escape($envName))\s") {
    return
  }
  Write-Info "Conda env '$envName' not found. Creating it (Postgres 16.10 + pgvector 0.8.1)..."
  conda create -n $envName -c conda-forge postgresql=16.10 pgvector=0.8.1 -y
}

function Ensure-Directories([string]$path) {
  if (-not (Test-Path $path)) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
  }
}

function Pg-IsReady([string]$envName, [int]$port, [string]$user) {
  try {
    $prefix = Get-CondaPrefix $envName
    $bin = Join-Path $prefix "Library\bin"
    $out = & (Join-Path $bin "pg_isready.exe") -h localhost -p $port -U $user 2>&1
    return [string]$out
  } catch {
    return $_.Exception.Message
  }
}

Assert-Command "conda"

Ensure-EnvExists $CondaEnvName

$prefix = Get-CondaPrefix $CondaEnvName
Write-Info "Using conda env: $CondaEnvName"
Write-Info "CONDA_PREFIX: $prefix"

$bin = Join-Path $prefix "Library\bin"
$initdb = Join-Path $bin "initdb.exe"
$pgCtl = Join-Path $bin "pg_ctl.exe"
$psql = Join-Path $bin "psql.exe"
$pgIsReady = Join-Path $bin "pg_isready.exe"

foreach ($exe in @($initdb, $pgCtl, $psql, $pgIsReady)) {
  if (-not (Test-Path $exe)) { throw "Missing expected executable: $exe" }
}

$rootDir = Split-Path -Parent $DataDir
Ensure-Directories $rootDir
Ensure-Directories $DataDir

$pgVersionFile = Join-Path $DataDir "PG_VERSION"
if (-not (Test-Path $pgVersionFile)) {
  Write-Info "Initializing database cluster in: $DataDir"

  $pwFile = Join-Path $env:TEMP ("pg_pw_{0}.txt" -f ([guid]::NewGuid().ToString('N')))
  Set-Content -Path $pwFile -Value $DbPassword -NoNewline

  try {
    & $initdb -D $DataDir -U $DbUser --auth-host=scram-sha-256 --auth-local=trust --pwfile=$pwFile
  } finally {
    Remove-Item -Force -ErrorAction SilentlyContinue $pwFile | Out-Null
  }
}

# Ensure port + listen address are set (last-one-wins if repeated)
$confPath = Join-Path $DataDir "postgresql.conf"
if (-not (Test-Path $confPath)) { throw "postgresql.conf not found at $confPath" }
Add-Content -Path $confPath -Value "`n# Graphbit local overrides`nlisten_addresses = '127.0.0.1'`nport = $Port`n"

# Start server
Write-Info "Starting Postgres on port $Port"
& $pgCtl -D $DataDir -l $LogFile -o "-p $Port" start -w -t 60

# Wait for readiness
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 1
  $ready = Pg-IsReady -envName $CondaEnvName -port $Port -user $DbUser
  if ($ready -match "accepting connections") {
    Write-Info "Postgres is ready"
    break
  }
  if ($i -eq 29) {
    throw "Postgres did not become ready. Last pg_isready output: $ready`nLog: $LogFile"
  }
}

# Enable extension + smoke test
Write-Info "Enabling pgvector extension and running smoke test"
$env:PGPASSWORD = $DbPassword
& $psql -h localhost -p $Port -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"
& $psql -h localhost -p $Port -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -c "SELECT extname, extversion FROM pg_extension WHERE extname='vector';"
& $psql -h localhost -p $Port -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -c "CREATE TEMP TABLE _pgvector_smoketest(id int, embedding vector(3)); INSERT INTO _pgvector_smoketest VALUES (1, '[1,2,3]'); SELECT * FROM _pgvector_smoketest;"

Write-Info "Done. Connection: postgresql://${DbUser}:*****@localhost:$Port/$DbName"
