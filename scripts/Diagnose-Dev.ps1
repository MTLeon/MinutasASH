[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$result = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    project_root = $root
    git_repository = Test-Path -LiteralPath (Join-Path $root ".git")
    virtual_environment = Test-Path -LiteralPath $python
    checks = [ordered]@{}
}

if ($result.virtual_environment) {
    $result.python = (& $python --version 2>&1 | Out-String).Trim()
    foreach ($module in @("pytest", "ruff", "mypy", "openpyxl", "pydantic", "requests", "docx")) {
        & $python -c "import $module" 2>$null
        $result.checks[$module] = ($LASTEXITCODE -eq 0)
    }
} else {
    $result.python = $null
}

$result.version = if (Test-Path -LiteralPath (Join-Path $root "VERSION.txt")) {
    (Get-Content -LiteralPath (Join-Path $root "VERSION.txt") -Raw).Trim()
} else {
    $null
}

$result | ConvertTo-Json -Depth 4
if (-not $result.git_repository -or -not $result.virtual_environment) { exit 1 }
if ($result.checks.Values -contains $false) { exit 1 }
exit 0
