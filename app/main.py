from fastapi import FastAPI
from .api import router as contact_router

app = FastAPI()

# Include the API routes
app.include_router(contact_router)

# Optional: Healthcheck or any other root endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the Contact API!"}
