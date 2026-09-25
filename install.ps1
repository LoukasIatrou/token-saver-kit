# Windows entry point. All the work happens in install.py.
$ErrorActionPreference = 'Stop'
foreach ($py in @('python', 'py', 'python3')) {
    if (Get-Command $py -ErrorAction SilentlyContinue) {
        & $py -c 'import sys; sys.exit(sys.version_info < (3, 11))'
        if ($LASTEXITCODE -eq 0) {
            & $py (Join-Path $PSScriptRoot 'install.py') @args
            exit $LASTEXITCODE
        }
    }
}
Write-Error 'Python 3.11+ is required: https://www.python.org/downloads/'
