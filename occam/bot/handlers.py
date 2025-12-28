"""
Feishu event handlers
Handles message events and menu events from Feishu
"""
import json
import re
from typing import Optional, Tuple
from urllib.parse import urlparse
from loguru import logger
from lark_oapi.api.im.v1.model import P2ImMessageReceiveV1

from occam.services.message_processor import MessageProcessorService


class FeishuEventHandler:
    """Handler for Feishu events"""
    
    def __init__(self, message_processor: MessageProcessorService):
        """
        Initialize event handler
        
        Args:
            message_processor: Message processor service for handling business logic
        """
        self.message_processor = message_processor
    
    def handle_message(self, event: P2ImMessageReceiveV1) -> Tuple[Optional[str], Optional[str]]:
        """
        Handle message receive event
        
        Args:
            event: Message event data
        
        Returns:
            Tuple of (reply_content, error_message)
            - If successful: (reply_content, None)
            - If error: (None, error_message)
        """
        try:
            message = event.event.message
            message_id = message.message_id
            message_type = message.message_type
            chat_id = event.event.message.chat_id
            
            logger.info(f"Processing message - ID: {message_id}, Type: {message_type}")
            
            # Extract message content
            content_json = json.loads(message.content)
            text_content = content_json.get('text', '')
            logger.info(f"Message content: {text_content}")
            
            # Parse URL and user notes from message
            url, user_notes = self._parse_message(text_content)
            
            if not url:
                logger.warning("No URL found in message")
                return "未找到有效的 URL，请发送包含链接的消息。", None
            
            # Process URL
            logger.info(f"Submitting processing task for URL: {url}")
            knowledge_entry, notion_url = self.message_processor.process_and_save(
                url=url,
                user_notes=user_notes
            )
            
            # Generate success notification
            notification = (
                f"✅ 已存入 Notion\n\n"
                f"标题: {knowledge_entry.title}\n"
                f"评分: {knowledge_entry.score}/100\n\n"
                f"查看: {notion_url}"
            )
            
            return notification, None
            
        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            return None, f"❌ 处理失败: {str(e)}"
    
    def handle_menu(self, event):
        """
        Handle bot menu event
        
        Args:
            event: Menu event data
        """
        logger.info(f"Received menu event: {event}")
    
    def _parse_message(self, text: str) -> Tuple[Optional[str], str]:
        """
        Parse URL and user notes from message text
        
        Args:
            text: Message text content
        
        Returns:
            Tuple of (url, user_notes)
        """
        # Find URL in text (supports http:// and https://)
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text)
        
        if not urls:
            return None, text
        
        url = urls[0]
        # Remove URL from text to get user notes
        user_notes = text.replace(url, '').strip()
        
        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return None, text
        except Exception:
            return None, text
        
        return url, user_notes

