$ErrorActionPreference = 'Stop'
$toolRoot = $PSScriptRoot
$repoRoot = Split-Path (Split-Path $toolRoot -Parent) -Parent
$backendRoot = Join-Path $repoRoot 'omnilead-be'
$stateRoot = Join-Path $backendRoot 'data/openclaw'
$logRoot = Join-Path $backendRoot 'data/local-runtime'
$secretRoot = Join-Path $backendRoot '.secrets'
$nodeDirectory = Join-Path $toolRoot '.runtime/node-v24.16.0-win-x64'
$nodeExecutable = Join-Path $nodeDirectory 'node.exe'
$entryPoint = Join-Path $toolRoot 'node_modules/openclaw/openclaw.mjs'
if (-not (Test-Path -LiteralPath $entryPoint)) { throw 'Run tools/openclaw/install.ps1 first.' }
$runtimeFile = Join-Path $logRoot 'openclaw-runtime.json'
if (Test-Path -LiteralPath $runtimeFile) {
    $previousRuntime = Get-Content -LiteralPath $runtimeFile -Raw | ConvertFrom-Json
    $previousProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($previousRuntime.pid)" -ErrorAction SilentlyContinue
    if ($previousProcess -and $previousProcess.CommandLine -like '*openclaw.mjs*gateway*') {
        throw 'OpenClaw is already starting or running. Existing process was preserved.'
    }
}
if (Get-NetTCPConnection -State Listen -LocalPort 18889 -ErrorAction SilentlyContinue) {
    throw 'Port 18889 is already in use. Existing process was preserved.'
}
foreach ($directory in @($stateRoot, $logRoot, $secretRoot)) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
$tokenPath = Join-Path $secretRoot 'openclaw-token'
if (-not (Test-Path -LiteralPath $tokenPath)) {
    $secretBytes = New-Object byte[] 32
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $random.GetBytes($secretBytes) } finally { $random.Dispose() }
    [BitConverter]::ToString($secretBytes).Replace('-', '').ToLowerInvariant() | Set-Content -LiteralPath $tokenPath -NoNewline
}
$browserExecutable = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
if (-not (Test-Path -LiteralPath $browserExecutable)) {
    $browserExecutable = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
}
if (-not (Test-Path -LiteralPath $browserExecutable)) { throw 'Install Edge or Chrome first.' }
$configPath = Join-Path $stateRoot 'openclaw.json'
$config = @{
    gateway = @{mode='local'; bind='loopback'; port=18889; auth=@{mode='token';token=(Get-Content -LiteralPath $tokenPath -Raw).Trim()}; controlUi=@{enabled=$false}}
    agents = @{defaults=@{workspace=(Join-Path $stateRoot 'workspace')}}
    tools = @{allow=@('browser')}
    plugins = @{allow=@('browser'); entries=@{browser=@{enabled=$true}}}
    browser = @{enabled=$true; headless=$false; evaluateEnabled=$false; executablePath=$browserExecutable; ssrfPolicy=@{dangerouslyAllowPrivateNetwork=$false; allowedHostnames=@('www.instagram.com','instagram.com','www.facebook.com','facebook.com','www.messenger.com','web.whatsapp.com','mail.google.com','accounts.google.com')}}
}
if (-not (Test-Path -LiteralPath $configPath)) {
    $config | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $configPath -Encoding UTF8
}
$previousPath = $env:PATH
$previousEnvironment = @{}
foreach ($name in @('OPENCLAW_STATE_DIR','OPENCLAW_CONFIG_PATH','OPENCLAW_EAGER_BROWSER_CONTROL_SERVER')) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
try {
    $env:PATH = "$nodeDirectory;$previousPath"
    $env:OPENCLAW_STATE_DIR = $stateRoot
    $env:OPENCLAW_CONFIG_PATH = $configPath
    $env:OPENCLAW_EAGER_BROWSER_CONTROL_SERVER = '1'
    $runtimeStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $gateway = Start-Process -FilePath $nodeExecutable -ArgumentList @(('"' + $entryPoint + '"'),'gateway','run','--port','18889','--bind','loopback') -WorkingDirectory $toolRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot "openclaw-$runtimeStamp.stdout.log") -RedirectStandardError (Join-Path $logRoot "openclaw-$runtimeStamp.stderr.log") -PassThru
    @{pid=$gateway.Id;started_at=$runtimeStamp;state_dir=$stateRoot;config_path=$configPath;version='2026.10.5';gateway_port=18889;browser_port=18891} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logRoot 'openclaw-runtime.json')
    Write-Output "OpenClaw gateway started on loopback port 18889 (PID $($gateway.Id)); browser control port 18891."
} finally {
    $env:PATH = $previousPath
    foreach ($name in $previousEnvironment.Keys) { [Environment]::SetEnvironmentVariable($name, $previousEnvironment[$name], 'Process') }
}
