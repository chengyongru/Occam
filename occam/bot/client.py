"""
Feishu Bot WebSocket client
Manages WebSocket connection and delegates events to handlers
"""
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from loguru import logger
import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
from lark_oapi.ws.client import Client as WSClient
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.api.im.v1.model import P2ImMessageReceiveV1

from occam.config import Settings
from occam.bot.handlers import FeishuEventHandler


class FeishuBotClient:
    """Feishu Bot client with WebSocket long connection support"""
    
    def __init__(
        self,
        settings: Settings,
        event_handler: FeishuEventHandler
    ):
        """
        Initialize Feishu Bot client
        
        Args:
            settings: Application settings
            event_handler: Event handler instance
        """
        self.settings = settings
        self.event_handler = event_handler
        
        # Create client using builder pattern (for API calls)
        self.client = lark.Client.builder() \
            .app_id(settings.feishu_app_id) \
            .app_secret(settings.feishu_app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        # Create event dispatcher handler for processing events
        self.dispatcher = EventDispatcherHandler.builder(
            encrypt_key=settings.feishu_encrypt_key,
            verification_token=settings.feishu_verification_token,
            level=lark.LogLevel.INFO
        ) \
        .register_p2_im_message_receive_v1(self._handle_message) \
        .register_p2_application_bot_menu_v6(self._handle_menu) \
        .build()
        
        # WebSocket client
        self.ws_client: Optional[WSClient] = None
        
        # Thread pool for async processing
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="occam-processor")
        
        logger.info("Feishu Bot client initialized")
    
    def _handle_message(self, event: P2ImMessageReceiveV1):
        """
        Internal message handler - delegates to event handler
        
        Args:
            event: Message event data
        """
        message = event.event.message
        message_id = message.message_id
        chat_id = event.event.message.chat_id
        
        # Send immediate acknowledgment
        self.reply_message(
            message_id=message_id,
            content="已收到，正在处理中...",
            receive_id=chat_id,
            receive_id_type="chat_id"
        )
        
        # Process asynchronously to avoid blocking WebSocket
        future = self.executor.submit(
            self._process_message_async,
            event
        )
    
    def _process_message_async(self, event: P2ImMessageReceiveV1):
        """
        Process message asynchronously
        
        Args:
            event: Message event data
        """
        message = event.event.message
        message_id = message.message_id
        chat_id = event.event.message.chat_id
        
        try:
            # Delegate to event handler
            reply_content, error_message = self.event_handler.handle_message(event)
            
            if error_message:
                # Send error notification
                self.reply_message(
                    message_id=message_id,
                    content=error_message,
                    receive_id=chat_id,
                    receive_id_type="chat_id"
                )
            elif reply_content:
                # Send success notification
                self.reply_message(
                    message_id=message_id,
                    content=reply_content,
                    receive_id=chat_id,
                    receive_id_type="chat_id"
                )
        except Exception as e:
            logger.exception(f"Error in async message processing: {e}")
            try:
                error_msg = f"❌ 处理失败: {str(e)}"
                self.reply_message(
                    message_id=message_id,
                    content=error_msg,
                    receive_id=chat_id,
                    receive_id_type="chat_id"
                )
            except Exception as reply_error:
                logger.exception(f"Error sending error notification: {reply_error}")
    
    def _handle_menu(self, event):
        """
        Internal menu handler - delegates to event handler
        
        Args:
            event: Menu event data
        """
        self.event_handler.handle_menu(event)
    
    def reply_message(
        self,
        message_id: str,
        content: str,
        receive_id: str,
        receive_id_type: str = "chat_id"
    ):
        """
        Reply to a message
        
        Args:
            message_id: Original message ID
            content: Reply content
            receive_id: Receive ID (chat_id or user_id)
            receive_id_type: Receive ID type, "chat_id" or "user_id"
        """
        try:
            logger.info(f"Replying to message {message_id} with content: {content}")
            logger.info(f"Receive ID: {receive_id}, Type: {receive_id_type}")
            
            request = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(receive_id)
                    .msg_type("text")
                    .content(json.dumps({"text": content}))
                    .build()
                ) \
                .build()
            
            response = self.client.im.v1.message.create(request)
            
            if response.success():
                logger.info(f"Successfully replied to message {message_id}")
            else:
                logger.error(f"Failed to reply message: {response.msg}, {response.request_id}")
                
        except Exception as e:
            logger.exception(f"Error replying message: {e}")
    
    def start(self):
        """Start the WebSocket long connection client"""
        try:
            logger.info("Starting Feishu Bot WebSocket long connection client...")
            logger.info(f"App ID: {self.settings.feishu_app_id}")
            
            # Create WebSocket client using official SDK
            self.ws_client = WSClient(
                app_id=self.settings.feishu_app_id,
                app_secret=self.settings.feishu_app_secret,
                log_level=lark.LogLevel.INFO,
                event_handler=self.dispatcher,
                auto_reconnect=True
            )
            
            logger.info("Feishu Bot WebSocket long connection client created")
            logger.info("Connecting to Feishu WebSocket server...")
            
            # Start the WebSocket connection
            self.ws_client.start()
            
        except Exception as e:
            logger.exception(f"Error starting WebSocket long connection client: {e}")
            raise
    
    def stop(self):
        """Stop the WebSocket long connection client"""
        try:
            logger.info("Stopping Feishu Bot WebSocket long connection client...")
            # Shutdown thread pool
            if self.executor:
                logger.info("Shutting down thread pool...")
                self.executor.shutdown(wait=True)
            logger.info("Feishu Bot WebSocket long connection client stopped")
        except Exception as e:
            logger.exception(f"Error stopping WebSocket long connection client: {e}")

