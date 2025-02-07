from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router as contact_router

app = FastAPI()
origins = ["<http://localhost:3000>"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include the API routes
app.include_router(contact_router)


# Optional: Healthcheck or any other root endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the Contact API!"}
