$ErrorActionPreference = "Stop"

param(
  [Parameter(Mandatory=$true)]
  [string]$HfSpaceId
)

if (-not $env:HF_TOKEN -and -not $env:HUGGINGFACEHUB_API_TOKEN) {
  Write-Error "Missing HF token. Set HF_TOKEN (or HUGGINGFACEHUB_API_TOKEN) before running."
}

if (-not $env:VERCEL_TOKEN) {
  Write-Error "Missing VERCEL_TOKEN. Set it before running."
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Error "Python launcher 'py' not found. Install Python first."
}

if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
  Write-Host "Installing Vercel CLI..."
  npm i -g vercel | Out-Host
}

Write-Host "Ensuring huggingface_hub is installed..."
py -m pip install -U huggingface_hub | Out-Host

Write-Host "Deploying backend to Hugging Face Space $HfSpaceId ..."
py scripts/deploy_free_backend.py --space-id $HfSpaceId | Out-Host

$hfUrl = "https://$($HfSpaceId.Replace('/', '-')).hf.space"
Write-Host "Backend URL: $hfUrl"

Push-Location frontend
try {
  Write-Host "Deploying frontend to Vercel (production)..."
  $deployOutput = vercel --prod --yes --token $env:VERCEL_TOKEN --build-env VITE_API_URL=$hfUrl 2>&1
  $deployOutput | Out-Host
}
finally {
  Pop-Location
}

Write-Host "Deployment attempt complete."
Write-Host "Set CORS_ORIGINS on HF Space to your Vercel domain if needed."
