$ErrorActionPreference = 'Stop'
$toolRoot = $PSScriptRoot
$nodeVersion = '24.16.0'
$runtimeRoot = Join-Path $toolRoot '.runtime'
$nodeDirectory = Join-Path $runtimeRoot "node-v$nodeVersion-win-x64"
$nodeExecutable = Join-Path $nodeDirectory 'node.exe'
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null

if (-not (Test-Path -LiteralPath $nodeExecutable)) {
    $archiveName = "node-v$nodeVersion-win-x64.zip"
    $archivePath = Join-Path $runtimeRoot $archiveName
    $baseUrl = "https://nodejs.org/dist/v$nodeVersion"
    $checksums = (Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/SHASUMS256.txt").Content
    $entry = @($checksums -split "`n" | Where-Object { $_.Trim().EndsWith("  $archiveName") })
    if ($entry.Count -ne 1) { throw 'Official Node checksum not found.' }
    $expectedHash = ($entry[0].Trim() -split '\s+')[0]
    Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/$archiveName" -OutFile $archivePath
    if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash.ToLowerInvariant()) {
        throw 'Node distribution checksum mismatch.'
    }
    Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimeRoot -Force
}

$previousPath = $env:PATH
try {
    $env:PATH = "$nodeDirectory;$previousPath"
    $installCommand = if (Test-Path -LiteralPath (Join-Path $toolRoot 'package-lock.json')) { 'ci' } else { 'install' }
    & $nodeExecutable (Join-Path $nodeDirectory 'node_modules/npm/bin/npm-cli.js') $installCommand --prefix $toolRoot --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'OpenClaw installation failed.' }
    & $nodeExecutable (Join-Path $toolRoot 'node_modules/openclaw/openclaw.mjs') --version
    if ($LASTEXITCODE -ne 0) { throw 'OpenClaw could not start.' }
} finally {
    $env:PATH = $previousPath
}
