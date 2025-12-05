$ProjectName = Split-Path (Get-Location) -Leaf
Write-Host "=== $ProjectName build & release ===" -ForegroundColor Cyan

$VersionPyPath = "$ProjectName/version.py"
$LatestWheelName = "$ProjectName-0-py3-none-any.whl"



function Save-TomlWithoutBOM {
    param (
        [string]$Path
    )

    if (!(Test-Path $Path)) {
        throw "File not found: $Path"
    }

    $content = Get-Content $Path -Raw
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $content, $utf8NoBom)
}

Save-TomlWithoutBOM "pyproject.toml"

python -m build

$wheel = Get-ChildItem dist\$ProjectName-*-py3-none-any.whl | Select-Object -First 1
Copy-Item $wheel.FullName dist\$ProjectName-0-py3-none-any.whl -Force