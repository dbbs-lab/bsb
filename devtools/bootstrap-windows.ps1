irm https://astral.sh/uv/install.ps1 | iex
if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
    irm https://get.scoop.sh | iex
} else {
    Write-Host "Scoop is already installed. Continuing..."
}
scoop install nodejs-lts
