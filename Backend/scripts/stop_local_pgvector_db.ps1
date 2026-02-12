[CmdletBinding()]
param(
  [string]$CondaEnvName = "graphbit-pgvector-db",
  [string]$DataDir = ""
)

$ErrorActionPreference = 'Stop'

if (-not $DataDir) {
  $baseDir = Join-Path (Join-Path $PSScriptRoot "..") ".local_pgvector_db"
  $DataDir = Join-Path $baseDir "data"
}

function Write-Info([string]$msg) { Write-Host "[local-pgvector-db] $msg" }

function Get-CondaPrefix([string]$envName) {
  $json = conda env list --json | ConvertFrom-Json
  if (-not $json.envs) { throw "Could not read conda env list (--json)" }
  $match = $json.envs | Where-Object { (Split-Path $_ -Leaf) -ieq $envName } | Select-Object -First 1
  if (-not $match) { throw "Conda env '$envName' not found" }
  return [string]$match
}

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
  throw "conda not found on PATH"
}

Write-Info "Stopping Postgres (if running)"
$prefix = Get-CondaPrefix $CondaEnvName
$bin = Join-Path $prefix "Library\bin"
$pgCtl = Join-Path $bin "pg_ctl.exe"
if (-not (Test-Path $pgCtl)) { throw "pg_ctl.exe not found: $pgCtl" }
& $pgCtl -D $DataDir stop -m fast
Write-Info "Stopped."
