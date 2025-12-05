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

Write-Host "✅ Latest wheel created: dist\$LatestWheelName"

# -----------------------------
# 9. Git tag
# -----------------------------

$tag = "v$newVersion"

git tag $tag
git push
git push origin $tag

# -----------------------------
# 10. make Release Notes из git log
# -----------------------------

$prevTag = git tag --sort=-v:refname | Select-Object -Skip 1 -First 1

if ($prevTag) {
    $releaseNotes = git log "$prevTag..$tag" --pretty=format:"- %s"
} else {
    $releaseNotes = git log $tag --pretty=format:"- %s"
}

if (-not $releaseNotes) {
    $releaseNotes = "- Initial release"
}

$releaseFile = "release_notes.txt"
Set-Content $releaseFile $releaseNotes -Encoding UTF8

Write-Host "✅ Release notes generated"

# -----------------------------
# 11. GitHub Release
# -----------------------------

gh release create $tag `
    dist/* `
    --title "Release $tag" `
    --notes-file $releaseFile

Remove-Item $releaseFile

Write-Host "✅✅✅ Release $tag created and uploaded for $ProjectName!" -ForegroundColor Green
