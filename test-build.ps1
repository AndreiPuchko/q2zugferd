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

if (Test-Path dist) {
    Remove-Item dist -Recurse -Force
}

python -m build

$wheel = Get-ChildItem dist\$ProjectName-*-py3-none-any.whl | Select-Object -First 1
Copy-Item $wheel.FullName dist\$ProjectName-0-py3-none-any.whl -Force
Copy-Item $ProjectName\version.py dist\version.py -Force
$latestFilePath = "dist\latest"
Set-Content -Path $latestFilePath -Value $wheel.Name -Encoding UTF8