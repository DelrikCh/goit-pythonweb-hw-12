from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .api import router as contact_router, limiter

app = FastAPI()
origins = ["<http://localhost:3000>"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Include the API routes
app.include_router(contact_router)


# Optional: Healthcheck or any other root endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the Contact API!"}
