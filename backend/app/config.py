"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    
    # Admin
    admin_password: str = ""
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # CORS
    cors_origins: str = "http://localhost:4200"
    
    # Data paths
    usda_foundation_path: str = "data/USDA_foundation.json"
    usda_sr_legacy_path: str = "data/USDA_sr_legacy.json"
    dishes_path: str = "data/dishes.xlsx"
    missing_dishes_path: str = "data/missing_dishes.json"
    test_queries_path: str = "data/test_queries.xlsx"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
