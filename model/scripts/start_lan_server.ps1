param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8000,
    [string]$RuntimeMode = "verified_kb",
    [string]$VerifiedKBPath = (
        ".\data\verified_kb\" +
        "material-001-gemini-smoke\" +
        "verified_kb.json"
    ),
    [string]$LLMBaseURL = (
        "https://generativelanguage.googleapis.com/" +
        "v1beta/openai"
    ),
    [string]$LLMModel = "gemini-3-flash-preview",
    [string]$MaterialThreshold = "0.10",
    [string]$CourseThreshold = "0.60",
    [string]$TopK = "3"
)

$ErrorActionPreference = "Stop"

$projectRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot ".."
    )
).Path

Set-Location $projectRoot

$pythonPath = Join-Path `
    $projectRoot `
    ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    throw (
        "Virtual environment Python not found: " +
        $pythonPath
    )
}

$resolvedKBPath = (
    Resolve-Path $VerifiedKBPath
).Path

if (-not $env:LOCAL_LLM_API_KEY) {
    throw (
        "LOCAL_LLM_API_KEY is not configured. " +
        "Set it in this PowerShell session first."
    )
}

$env:MODEL_RUNTIME_MODE = $RuntimeMode
$env:VERIFIED_KB_PATH = $resolvedKBPath
$env:LOCAL_LLM_BASE_URL = $LLMBaseURL
$env:LOCAL_LLM_MODEL = $LLMModel
$env:MATERIAL_SCOPE_THRESHOLD = $MaterialThreshold
$env:COURSE_SCOPE_THRESHOLD = $CourseThreshold
$env:RAG_TOP_K = $TopK

$privateIPv4Addresses = @(
    Get-NetIPAddress `
        -AddressFamily IPv4 `
        -AddressState Preferred `
        -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -ne "127.0.0.1" -and
        $_.IPAddress -notlike "169.254.*"
    } |
    Select-Object -ExpandProperty IPAddress -Unique
)

Write-Host ""
Write-Host "Learning Companion LAN Prototype"
Write-Host "--------------------------------"
Write-Host "Python:            $pythonPath"
Write-Host "Runtime mode:      $env:MODEL_RUNTIME_MODE"
Write-Host "Verified KB:       $env:VERIFIED_KB_PATH"
Write-Host "LLM model:         $env:LOCAL_LLM_MODEL"
Write-Host "Material threshold:$env:MATERIAL_SCOPE_THRESHOLD"
Write-Host "Course threshold:  $env:COURSE_SCOPE_THRESHOLD"
Write-Host "RAG top-k:         $env:RAG_TOP_K"
Write-Host ""

Write-Host "Local endpoints:"
Write-Host "  http://127.0.0.1:$Port/docs"
Write-Host "  http://127.0.0.1:$Port/health"

if ($privateIPv4Addresses.Count -gt 0) {
    Write-Host ""
    Write-Host "LAN endpoints:"

    foreach ($ipAddress in $privateIPv4Addresses) {
        Write-Host "  http://${ipAddress}:$Port/docs"
        Write-Host "  http://${ipAddress}:$Port/health"
    }
}

Write-Host ""
Write-Host "Press Ctrl+C to stop the server."
Write-Host ""

& $pythonPath `
    -m uvicorn `
    src.service.main:app `
    --host $HostAddress `
    --port $Port