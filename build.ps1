param (
    [ValidateSet("major", "minor", "patch")]
    [string]$Bump = "patch"
)

Write-Host "=== q2zugferd build & release ===" -ForegroundColor Cyan

# -----------------------------
# 0. Проверка git-статуса
# -----------------------------

$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Error "❌ The working directory is not clean! Commit or revert the changes:"
    git status -s
    exit 1
}

Write-Host "✅ Git working tree clean" -ForegroundColor Green

# -----------------------------
# 1. Получаем текущую версию
# -----------------------------

$versionFile = "pyproject.toml"
$content = Get-Content $versionFile

$versionLine = $content | Where-Object { $_ -match '^version\s*=' }
if (-not $versionLine) {
    Write-Error "version not found in pyproject.toml"
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
# 2. Записываем новую версию в pyproject.toml
# -----------------------------

$content = $content -replace 'version\s*=\s*".*"', "version = `"$newVersion`""
Set-Content $versionFile $content -Encoding UTF8

# -----------------------------
# 3. Генерация q2zugferd/version.py
# -----------------------------

$versionPyPath = "q2zugferd/version.py"

$versionPyContent = @"
__version__ = "$newVersion"
"@

Set-Content $versionPyPath $versionPyContent -Encoding UTF8

Write-Host "* version.py generated: $versionPyPath"

# -----------------------------
# 4. Git commit версии
# -----------------------------

git add pyproject.toml q2zugferd/version.py
git commit -m "chore: bump version to v$newVersion"

# -----------------------------
# 5. Build
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
# 6. Git tag
# -----------------------------

$tag = "v$newVersion"

git tag $tag
git push
git push origin $tag

# -----------------------------
# 7. Генерация Release Notes из git log
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

Write-Host "✅ Release notes generated from git log"

# -----------------------------
# 8. GitHub Release (через gh)
# -----------------------------

gh release create $tag `
    dist/* `
    --title "Release $tag" `
    --notes-file $releaseFile

Remove-Item $releaseFile

Write-Host "✅✅✅ Release $tag created and uploaded!" -ForegroundColor Green
