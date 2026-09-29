$ErrorActionPreference = "Stop"

$repo = $PSScriptRoot
$output = Join-Path $repo "touch_counting_portable.zip"
$stage = Join-Path $env:TEMP ("touch_counting_pack_" + [guid]::NewGuid().ToString("N"))
$bundle = Join-Path $stage "touch_counting_portable"

try {
    New-Item -ItemType Directory -Path $bundle | Out-Null

    Write-Host "Packing Conda environment touchCounting..."
    conda-pack -n touchCounting -o (Join-Path $stage "environment.zip") --format zip --force
    Copy-Item (Join-Path $stage "environment.zip") -Destination $bundle

    Get-ChildItem -Force $repo |
        Where-Object { $_.Name -notin @(".git", ".gitignore", "__pycache__", "touch_counting_portable.zip") } |
        Copy-Item -Destination $bundle -Recurse -Force

    if (Test-Path $output) {
        Remove-Item $output -Force
    }
    Compress-Archive -Path (Join-Path $bundle "*") -DestinationPath $output -CompressionLevel Optimal

    $sizeMb = [math]::Round((Get-Item $output).Length / 1MB, 2)
    Write-Host "Created: $output ($sizeMb MB)" -ForegroundColor Green
}
finally {
    if (Test-Path $stage) {
        Remove-Item $stage -Recurse -Force
    }
}