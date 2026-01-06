"""Application configuration."""
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    openai_api_key: str = ""
    deepseek_api_key:  str = ""
    
    # Admin
    admin_password: str = ""
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # CORS
    cors_origins: str = "http://localhost:4200"
    
    # Data paths
    usda_db_path: str = str(BASE_DIR / "data" / "usda.db")
    dishes_path: str = str(BASE_DIR / "data" / "dishes.xlsx")
    missing_dishes_path:  str = str(BASE_DIR / "data" / "missing_dishes.json")
    test_queries_path:  str = str(BASE_DIR / "data" / "test_queries.xlsx")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def cors_origins_list(self) -> List[str]: 
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()