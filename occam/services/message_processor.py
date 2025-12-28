"""
Message processing service - Business logic orchestration
Coordinates scraping, AI processing, and storage services
"""
from typing import Optional
from loguru import logger

from occam.services.scraper import ScraperService
from occam.services.ai_processor import AIProcessorService
from occam.services.notion_storage import NotionStorageService
from occam.models import KnowledgeEntry
from occam.config import Settings


class MessageProcessorService:
    """Service for processing messages and orchestrating the knowledge extraction workflow"""
    
    def __init__(
        self,
        scraper: Optional[ScraperService] = None,
        ai_processor: Optional[AIProcessorService] = None,
        notion_storage: Optional[NotionStorageService] = None,
        settings: Optional[Settings] = None
    ):
        """
        Initialize message processor service
        
        Args:
            scraper: Scraper service instance (if None, will create new)
            ai_processor: AI processor service instance (if None, will create new)
            notion_storage: Notion storage service instance (if None, will create new)
            settings: Application settings (if None, will load from environment)
        """
        if settings is None:
            from occam.config import get_settings
            settings = get_settings()
        
        self.settings = settings
        self.scraper = scraper or ScraperService()
        self.ai_processor = ai_processor or AIProcessorService(settings)
        self.notion_storage = notion_storage or NotionStorageService(settings)
    
    def process_and_save(self, url: str, user_notes: str = "") -> tuple[KnowledgeEntry, str]:
        """
        Process URL and save to Notion
        
        This method orchestrates the complete workflow:
        1. Fetch webpage content
        2. Process with AI
        3. Save to Notion
        
        Args:
            url: Article URL to process
            user_notes: User's notes or thoughts
        
        Returns:
            Tuple of (KnowledgeEntry, notion_page_url)
        
        Raises:
            Exception: If any step fails
        """
        try:
            logger.info(f"Starting process_and_save for URL: {url}")
            
            # Step 1: Fetch webpage content
            logger.info("Step 1: Fetching webpage content...")
            raw_content = self.scraper.fetch_content(url)
            logger.info(f"Fetched content, length: {len(raw_content)} characters")
            
            # Step 2: Process with AI
            logger.info("Step 2: Processing with AI...")
            knowledge_entry = self.ai_processor.process(
                raw_content=raw_content,
                user_notes=user_notes,
                url=url
            )
            logger.info(f"AI processing complete: {knowledge_entry.title}")
            
            # Step 3: Save to Notion
            logger.info("Step 3: Saving to Notion...")
            notion_url = self.notion_storage.create_page(knowledge_entry)
            logger.info(f"Saved to Notion: {notion_url}")
            
            logger.info("process_and_save completed successfully")
            return knowledge_entry, notion_url
            
        except Exception as e:
            logger.exception(f"Error in process_and_save: {e}")
            raise

