[CmdletBinding()]
param(
  [string]$PgConfigPath = "",
  [string]$PgvectorTag = "",  # e.g. "v0.7.4"; if empty tries GitHub latest
  [string]$EnvFile = "$(Join-Path $PSScriptRoot ".." ".env")",
  [switch]$SkipEnableExtension,
  [switch]$SkipBuildToolsInstall
)

$ErrorActionPreference = 'Stop'

function Write-Info([string]$msg) { Write-Host "[pgvector] $msg" }

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

function Resolve-PgConfig([string]$explicit) {
  if ($explicit) {
    if (-not (Test-Path $explicit)) { throw "PgConfigPath not found: $explicit" }
    return (Resolve-Path $explicit).Path
  }

  $cmd = Get-Command pg_config -ErrorAction SilentlyContinue
  if (-not $cmd) {
    throw "pg_config not found on PATH. Provide -PgConfigPath (e.g. 'S:\\apps\\PostgreSQL\\18\\bin\\pg_config.exe')."
  }
  return $cmd.Source
}

function Get-VsDevCmd() {
  $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
  if (-not (Test-Path $vswhere)) {
    return $null
  }

  $installPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
  if (-not $installPath) {
    return $null
  }

  $devCmd = Join-Path $installPath "Common7\Tools\VsDevCmd.bat"
  if (Test-Path $devCmd) { return $devCmd }
  return $null
}

function Ensure-BuildTools([switch]$skipInstall) {
  $devCmd = Get-VsDevCmd
  if ($devCmd) { return $devCmd }

  throw (
    "MSVC Build Tools were not detected. pgvector must be compiled with MSVC on Windows for a native PostgreSQL install. " +
    "Install 'Visual Studio Build Tools 2022' with C++ (MSVC) support, then re-run this script from a new terminal. " +
    "If you want to avoid MSVC entirely, use the conda-based local Postgres+pgvector script instead."
  )
}

function Get-LatestPgvectorTag() {
  try {
    $headers = @{ "User-Agent" = "Graphbit-pgvector-installer" }
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/pgvector/pgvector/releases/latest" -Headers $headers
    if ($release.tag_name) { return [string]$release.tag_name }
  } catch {
    return $null
  }
  return $null
}

function Invoke-Cmd([string]$cmdLine, [string]$workingDir) {
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = "cmd.exe"
  $psi.Arguments = "/c " + $cmdLine
  $psi.WorkingDirectory = $workingDir
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $psi
  [void]$p.Start()
  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $p.WaitForExit()

  if ($stdout) { Write-Host $stdout }
  if ($stderr) { Write-Host $stderr }
  if ($p.ExitCode -ne 0) { throw "Command failed (exit $($p.ExitCode)): $cmdLine" }
}

$pgConfig = Resolve-PgConfig $PgConfigPath
Write-Info "Using pg_config: $pgConfig"

$pgVersion = & $pgConfig --version
$pgBindir = & $pgConfig --bindir
Write-Info "PostgreSQL: $pgVersion"
Write-Info "bindir: $pgBindir"

$psql = Join-Path $pgBindir "psql.exe"
if (-not (Test-Path $psql)) {
  $psqlCmd = Get-Command psql -ErrorAction SilentlyContinue
  if ($psqlCmd) { $psql = $psqlCmd.Source }
}
if (-not (Test-Path $psql)) { throw "psql not found. Expected at: $psql" }

$tag = $PgvectorTag
if (-not $tag) {
  $tag = Get-LatestPgvectorTag
}
if (-not $tag) {
  # fallback (stable-ish) if GitHub API blocked/offline
  $tag = "v0.7.4"
  Write-Info "Could not query GitHub for latest tag; falling back to $tag"
} else {
  Write-Info "Using pgvector tag: $tag"
}

$workRoot = Join-Path $PSScriptRoot "..\.tmp\pgvector"
New-Item -ItemType Directory -Force -Path $workRoot | Out-Null

$zipPath = Join-Path $workRoot "pgvector-$tag.zip"
$srcDir = Join-Path $workRoot "pgvector-$tag"

if (-not (Test-Path $zipPath)) {
  $zipUrl = "https://github.com/pgvector/pgvector/archive/refs/tags/$tag.zip"
  Write-Info "Downloading $zipUrl"
  Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
}

if (Test-Path $srcDir) {
  Remove-Item -Recurse -Force $srcDir
}
Write-Info "Extracting source"
Expand-Archive -Force -Path $zipPath -DestinationPath $workRoot

# GitHub zips extract to pgvector-<tag-without-v>
$extracted = Get-ChildItem -Path $workRoot -Directory | Where-Object { $_.Name -like "pgvector-*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $extracted) { throw "Could not locate extracted pgvector directory in $workRoot" }

$pgvectorDir = $extracted.FullName
Write-Info "Source dir: $pgvectorDir"

$vsDevCmd = Ensure-BuildTools -skipInstall:$SkipBuildToolsInstall
Write-Info "Using VS dev cmd: $vsDevCmd"

# Build+install under VS dev environment
$buildCmd = '"{0}" -arch=amd64 && cd /d "{1}" && set "PG_CONFIG={2}" && nmake /f Makefile USE_PGXS=1 && nmake /f Makefile USE_PGXS=1 install' -f $vsDevCmd, $pgvectorDir, $pgConfig
Write-Info "Building and installing pgvector (this can take 1-3 minutes)"
Invoke-Cmd -cmdLine $buildCmd -workingDir $pgvectorDir

Write-Info "pgvector installed into this PostgreSQL instance."

if (-not $SkipEnableExtension) {
  $envMap = Get-EnvMap $EnvFile
  if (-not $envMap.ContainsKey('DATABASE_URL')) {
    throw "DATABASE_URL not found in $EnvFile"
  }

  $dbUrl = $envMap['DATABASE_URL']
  # SQLAlchemy URL -> libpq URL
  $dbUrl = $dbUrl -replace '^postgresql\+psycopg://', 'postgresql://'
  $dbUrl = $dbUrl -replace '^postgresql\+asyncpg://', 'postgresql://'

  Write-Info "Enabling extension in database via psql"

  # Use PGPASSWORD when possible (psql may also take it via URL, but this is consistent)
  if ($envMap.ContainsKey('POSTGRES_PASSWORD')) {
    $env:PGPASSWORD = $envMap['POSTGRES_PASSWORD']
  }

  & $psql $dbUrl -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;" | Write-Host
  & $psql $dbUrl -v ON_ERROR_STOP=1 -c "SELECT extname, extversion FROM pg_extension WHERE extname='vector';" | Write-Host
  & $psql $dbUrl -v ON_ERROR_STOP=1 -c "CREATE TEMP TABLE _pgvector_smoketest(id int, embedding vector(3)); INSERT INTO _pgvector_smoketest VALUES (1, '[1,2,3]'); SELECT * FROM _pgvector_smoketest;" | Write-Host

  Write-Info "Extension enabled and smoke test passed."
}

Write-Info "Done."
