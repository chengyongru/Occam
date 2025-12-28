"""
Configuration settings management
Centralized configuration using environment variables
"""
import os
from pathlib import Path
from typing import Optional
from functools import lru_cache
from dotenv import load_dotenv


class Settings:
    """Application settings loaded from environment variables"""
    
    # Feishu configuration
    feishu_app_id: str
    feishu_app_secret: str
    feishu_encrypt_key: str = ""
    feishu_verification_token: str = ""
    
    # LLM configuration
    llm_base_url: str
    llm_api_key: str
    llm_model: str = "deepseek-chat"
    llm_timeout: float = 120.0
    llm_temperature: float = 0.7
    llm_max_retries: int = 2
    
    # Notion configuration
    notion_token: str
    notion_database_id: str
    # Notion property name mappings (optional, for custom property names)
    # Format: "internal_name:notion_property_name"
    # Example: "NOTION_PROPERTY_TITLE:Name" means use "Name" as the title property in Notion
    notion_property_title: str = "Title"
    notion_property_ai_summary: str = "AI Summary"
    notion_property_critical_thinking: str = "Critical Thinking"
    notion_property_tags: str = "Tags"
    notion_property_score: str = "Score"
    notion_property_url: str = "URL"
    
    def __init__(self):
        """Load settings from environment variables"""
        # Load .env file from backend directory
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()
        
        # Feishu settings
        self.feishu_app_id = os.getenv('FEISHU_APP_ID', '')
        self.feishu_app_secret = os.getenv('FEISHU_APP_SECRET', '')
        self.feishu_encrypt_key = os.getenv('FEISHU_ENCRYPT_KEY', '')
        self.feishu_verification_token = os.getenv('FEISHU_VERIFICATION_TOKEN', '')
        
        # LLM settings
        self.llm_base_url = os.getenv('BASE_URL', '')
        self.llm_api_key = os.getenv('API_KEY', '')
        self.llm_model = os.getenv('LLM_MODEL', 'deepseek-chat')
        self.llm_timeout = float(os.getenv('LLM_TIMEOUT', '120.0'))
        self.llm_temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
        self.llm_max_retries = int(os.getenv('LLM_MAX_RETRIES', '2'))
        
        # Normalize base_url - ensure it ends with /v1
        # According to CloseAI docs, base_url must include /v1 suffix
        if self.llm_base_url:
            self.llm_base_url = self.llm_base_url.rstrip('/')
            if not self.llm_base_url.endswith('/v1'):
                self.llm_base_url = f"{self.llm_base_url}/v1"
        
        # Notion settings
        self.notion_token = os.getenv('NOTION_TOKEN', '')
        self.notion_database_id = os.getenv('NOTION_DATABASE_ID', '')
        # Notion property name mappings (can be customized via env vars)
        self.notion_property_title = os.getenv('NOTION_PROPERTY_TITLE', 'Title')
        self.notion_property_ai_summary = os.getenv('NOTION_PROPERTY_AI_SUMMARY', 'AI Summary')
        self.notion_property_critical_thinking = os.getenv('NOTION_PROPERTY_CRITICAL_THINKING', 'Critical Thinking')
        self.notion_property_tags = os.getenv('NOTION_PROPERTY_TAGS', 'Tags')
        self.notion_property_score = os.getenv('NOTION_PROPERTY_SCORE', 'Score')
        self.notion_property_url = os.getenv('NOTION_PROPERTY_URL', 'URL')
        
        # Validate required settings
        self._validate()
    
    def _validate(self):
        """Validate required settings"""
        required = {
            'FEISHU_APP_ID': self.feishu_app_id,
            'FEISHU_APP_SECRET': self.feishu_app_secret,
            'BASE_URL': self.llm_base_url,
            'API_KEY': self.llm_api_key,
            'NOTION_TOKEN': self.notion_token,
            'NOTION_DATABASE_ID': self.notion_database_id,
        }
        
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please set them in .env file or environment variables"
            )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

