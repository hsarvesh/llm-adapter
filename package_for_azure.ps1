$zipPath = "deploy.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }

# Define files and folders to include
$includeList = @(
    "llm", 
    "models", 
    "parsers", 
    "static", 
    "telemetry", 
    "utils",
    "main.py",
    "config.py",
    "function_app.py",
    "host.json",
    "requirements.txt"
)

Write-Host "Creating deployment zip: $zipPath..." -ForegroundColor Cyan

# Create the zip archive
Compress-Archive -Path $includeList -DestinationPath $zipPath -Force

Write-Host "Success! Created $zipPath" -ForegroundColor Green
Write-Host "You can now upload this file to the Azure Portal via 'Advanced Tools' (Kudu) or use the Azure CLI." -ForegroundColor Yellow
