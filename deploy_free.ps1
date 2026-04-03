param(
  [Parameter(Mandatory=$true)]
  [string]$HfSpaceId
)

$ErrorActionPreference = "Stop"

$hfToken = $env:HF_TOKEN
if (-not $hfToken) { $hfToken = $env:HUGGINGFACEHUB_API_TOKEN }

if (-not $hfToken) {
  if (Get-Command hf -ErrorAction SilentlyContinue) {
    try {
      hf auth whoami | Out-Null
      Write-Host "HF token env var not set, using Hugging Face CLI login session."
    }
    catch {
      Write-Error "Hugging Face not authenticated. Run: hf auth login or set HF_TOKEN."
    }
  }
  else {
    Write-Error "Hugging Face CLI not found and HF token not set."
  }
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
  if ($env:VERCEL_TOKEN) {
    $deployOutput = vercel --prod --yes --token $env:VERCEL_TOKEN --build-env VITE_API_URL=$hfUrl 2>&1
  }
  else {
    Write-Host "VERCEL_TOKEN not set, using existing Vercel CLI login session."
    $deployOutput = vercel --prod --yes --build-env VITE_API_URL=$hfUrl 2>&1
  }
  $deployOutput | Out-Host
}
finally {
  Pop-Location
}

Write-Host "Deployment attempt complete."
Write-Host "Set CORS_ORIGINS on HF Space to your Vercel domain if needed."
