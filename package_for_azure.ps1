$zipPath = "deploy.zip"
$appName = "llm-adapter-ddanhucxfdftf2cv"

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

Write-Host "--- Preparing Deployment ---" -ForegroundColor Cyan
Write-Host "Creating deployment zip: $zipPath..." -ForegroundColor White

# Create the zip archive
Compress-Archive -Path $includeList -DestinationPath $zipPath -Force

Write-Host "`nSuccess! Created $zipPath" -ForegroundColor Green

Write-Host "`n--- Deployment Instructions ---" -ForegroundColor Cyan
Write-Host "To deploy the code AND sync the settings (including Azure OpenAI keys), run:" -ForegroundColor Yellow
Write-Host "func azure functionapp publish $appName --publish-local-settings -y" -ForegroundColor White

Write-Host "`nVerification Endpoints:" -ForegroundColor Cyan
Write-Host "Dashboard: https://$appName.azurewebsites.net/static/index.html" -ForegroundColor White
Write-Host "Health:    https://$appName.azurewebsites.net/health" -ForegroundColor White
Write-Host "Swagger:   https://$appName.azurewebsites.net/docs" -ForegroundColor White
