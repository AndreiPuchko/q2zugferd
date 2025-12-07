param (
    [ValidateSet("major", "minor", "patch")]
    [string]$Bump = "patch"
)

# -----------------------------
# 0. define project name
# -----------------------------

$ProjectName = Split-Path (Get-Location) -Leaf
Write-Host "=== $ProjectName build & release ===" -ForegroundColor Cyan

$VersionPyPath = "$ProjectName/version.py"
$LatestWheelName = "$ProjectName-0-py3-none-any.whl"

# -----------------------------
# 1. check git-status
# -----------------------------

$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Error "❌ The working directory is not clean! Commit or revert the changes:"
    git status -s
    exit 1
}

Write-Host "✅ Git working tree clean" -ForegroundColor Green

# -----------------------------
# 2. get current version
# -----------------------------

$versionFile = "pyproject.toml"
$content = Get-Content $versionFile

$versionLine = $content | Where-Object { $_ -match '^version\s*=' }
if (-not $versionLine) {
    Write-Error "❌ version not found in pyproject.toml"
    exit 1
}

$version = ($versionLine -split '"')[1]
Write-Host "Current version: $version"

$parts = $version.Split(".")
$major = [int]$parts[0]
$minor = [int]$parts[1]
$patch = [int]$parts[2]

switch ($Bump) {
    "major" { $major++; $minor = 0; $patch = 0 }
    "minor" { $minor++; $patch = 0 }
    "patch" { $patch++ }
}

$newVersion = "$major.$minor.$patch"
Write-Host "New version: $newVersion" -ForegroundColor Green

# -----------------------------
# 3. write new version into pyproject.toml
# -----------------------------

$content = $content -replace 'version\s*=\s*".*"', "version = `"$newVersion`""
Set-Content $versionFile $content -Encoding UTF8

# -----------------------------
# 4. update version.py
# -----------------------------

$versionPyContent = @"
__version__ = "$newVersion"
"@

Set-Content $VersionPyPath $versionPyContent -Encoding UTF8
Write-Host "✅ version.py generated: $VersionPyPath"

# -----------------------------
# 5. remove BOM from pyproject.toml
# -----------------------------

function Save-TomlWithoutBOM {
    param ([string]$Path)

    $content = Get-Content $Path -Raw
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $content, $utf8NoBom)
}

Save-TomlWithoutBOM "pyproject.toml"

# -----------------------------
# 6. Git commit
# -----------------------------

git add pyproject.toml $VersionPyPath
git commit -m "chore: bump version to v$newVersion"

# -----------------------------
# 7. Build
# -----------------------------

if (Test-Path dist) {
    Remove-Item dist -Recurse -Force
}

python -m build
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Build failed"
    exit 1
}

# -----------------------------
# 8. make latest-wheel
# -----------------------------

$wheel = Get-ChildItem dist\*-py3-none-any.whl | Select-Object -First 1
Copy-Item $wheel.FullName "dist\$LatestWheelName" -Force

Copy-Item $ProjectName\version.py dist\version.py -Force
$latestFilePath = "dist\latest"
Set-Content -Path $latestFilePath -Value $wheel.Name -Encoding UTF8


Write-Host "✅ Latest wheel created: dist\$LatestWheelName"

# -----------------------------
# 9. Git tag
# -----------------------------

$tag = "v$newVersion"

git tag $tag
git push
git push origin $tag

# --- 6. Generate Release Notes ---
$previousTag = git describe --tags --abbrev=0 $tag~1 2>$null

if ($LASTEXITCODE -eq 0 -and $previousTag) {
    $commits = git log $previousTag..HEAD --pretty=format:"%s"
} else {
    $commits = git log --pretty=format:"%s"
}

# Initialize sections
$added = @()
$fixed = @()
$changed = @()
$others = @()

foreach ($c in $commits) {
    if ($c -match "^feat") { $added += "- $c" }
    elseif ($c -match "^fix") { $fixed += "- $c" }
    elseif ($c -match "^refactor|^chore") { $changed += "- $c" }
    else { $others += "- $c" }
}

$releaseNotes = "## Release v$version`n`n"
if ($added.Count -gt 0) { $releaseNotes += "### Added`n" + ($added -join "`n") + "`n`n" }
if ($fixed.Count -gt 0) { $releaseNotes += "### Fixed`n" + ($fixed -join "`n") + "`n`n" }
if ($changed.Count -gt 0) { $releaseNotes += "### Changed`n" + ($changed -join "`n") + "`n`n" }
if ($others.Count -gt 0) { $releaseNotes += "### Other`n" + ($others -join "`n") + "`n`n" }

# --- 7. Prepare current version assets ---
$whlFile = Get-ChildItem dist | Where-Object { $_.Name -like "*$version*.whl" } | Select-Object -First 1
$tarFile = Get-ChildItem dist | Where-Object { $_.Name -like "*$version*.tar.gz" } | Select-Object -First 1
$assets = @()
if ($whlFile) { $assets += $whlFile.FullName }
if ($tarFile) { $assets += $tarFile.FullName }

# --- 8. Create GitHub Release via gh ---
$ghExists = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghExists) {
    Write-Host "ERROR: GitHub CLI (gh) is not installed. Skipping GitHub Release."
    Write-Host "Install with: winget install --id GitHub.cli"
    exit 0
}

$existingRelease = gh release view $tag 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "GitHub Release $tag already exists. Skipping release creation."
} else {
    Write-Host "Creating GitHub Release $tag ..."

    gh release create $tag $assets `
        --title "v$version" `
        --notes "$releaseNotes"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "GitHub Release $tag successfully created."
    } else {
        Write-Host "ERROR: Failed to create GitHub Release."
    }
}