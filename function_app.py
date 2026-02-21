import azure.functions as func
from main import app as fastapi_app

# The AsgiFunctionApp allows you to run FastAPI apps directly in Azure Functions
# This is the entry point for the Function App
app = func.AsgiFunctionApp(
    app=fastapi_app, 
    http_auth_level=func.AuthLevel.ANONYMOUS
)
