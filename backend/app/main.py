from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import chat, countries, admin
from app.data.data_loader import load_all_data

app = FastAPI(
    title="Arabic Calorie Estimation API",
    description="API for estimating calories in Arabic dishes",
    version="1.0.0"
)

# CORS Configuration
origins = [
    "http://localhost:4200",
    "http://localhost:3000",
    "https://csci599-calories-estimation-chatbot-2.onrender.com",  # Your frontend
]

# Add origins from environment variable
if settings.cors_origins:
    for origin in settings.cors_origins.split(","):
        origin = origin.strip()
        if origin and origin not in origins: 
            origins.append(origin)

print(f"🌐 CORS Origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api")
app.include_router(countries.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Load data on startup."""
    load_all_data()

@app.get("/")
async def root():
    return {"message": "Arabic Calorie Estimation API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}