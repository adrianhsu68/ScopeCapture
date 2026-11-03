param([string]$Python = "py")
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    $pythonArgs = @()
    if ([IO.Path]::GetFileNameWithoutExtension($Python) -eq "py") { $pythonArgs = @("-3") }
    & $Python @pythonArgs -m unittest discover -s test -t .
    if ($LASTEXITCODE -ne 0) { throw "Tests failed" }
    $versionFile = Join-Path $PSScriptRoot 'version-info.txt'
    & $Python @pythonArgs -m PyInstaller --noconfirm --clean --onefile --windowed --name ScopeCapture --version-file $versionFile --add-data "$PSScriptRoot\LICENSE;." --add-data "$PSScriptRoot\THIRD-PARTY-NOTICES.txt;." --add-data "$PSScriptRoot\licenses;licenses" --distpath release --workpath build --specpath build scope_capture.py
    if ($LASTEXITCODE -ne 0) { throw "EXE build failed" }
    Copy-Item -LiteralPath docs\guide.en.txt -Destination release\README-English.txt
    Copy-Item -LiteralPath docs\guide.zh-TW.txt -Destination release\README-Chinese.txt
    Copy-Item -LiteralPath LICENSE,THIRD-PARTY-NOTICES.txt -Destination release
    Copy-Item -LiteralPath licenses -Destination release -Recurse -Force
    Compress-Archive -LiteralPath release\ScopeCapture.exe,release\README-English.txt,release\README-Chinese.txt,release\LICENSE,release\THIRD-PARTY-NOTICES.txt,release\licenses -DestinationPath release\ScopeCapture-Windows-x64.zip -Force
    $checksums = foreach ($file in @("ScopeCapture.exe", "ScopeCapture-Windows-x64.zip")) {
        $hash = (Get-FileHash -LiteralPath (Join-Path release $file) -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash  $file"
    }
    [IO.File]::WriteAllLines((Join-Path $PSScriptRoot 'release\SHA256SUMS.txt'), $checksums, [Text.UTF8Encoding]::new($false))
    Write-Host "Built: $PSScriptRoot\release\ScopeCapture-Windows-x64.zip"
} finally {
    Pop-Location
}
