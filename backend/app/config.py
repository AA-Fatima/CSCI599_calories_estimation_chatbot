from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # API Keys
    openai_api_key: str = ""
    
    # Admin
    admin_password: str = ""
    
    # CORS
    cors_origins: str = "http://localhost:4200"
    
    # Paths
    dishes_path: Path = Path(__file__).parent.parent / "data" / "dishes.xlsx"
    usda_db_path: Path = Path(__file__).parent.parent / "data" / "usda.db"
    missing_dishes_path:  Path = Path(__file__).parent.parent / "data" / "missing_dishes.json"
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()