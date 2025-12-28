"""
Feishu Bot with WebSocket Long Connection
Using official lark-oapi SDK WebSocket client
"""
import os
import json
import sys
from pathlib import Path
from loguru import logger

# Configure loguru logger format with file path and line number for VSCode navigation
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{file.path}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
    level="INFO",
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# Load environment variables from .env file
from dotenv import load_dotenv
# Load .env file from backend directory
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"Loaded .env file from {env_path}")
else:
    # Try to load from current directory
    load_dotenv()

# Import lark_oapi SDK
import lark_oapi as lark
from lark_oapi.api.im.v1.model import P2ImMessageReceiveV1
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
from lark_oapi.ws.client import Client as WSClient


class FeishuBot:
    """Feishu Bot client with WebSocket long connection support"""
    
    def __init__(self, app_id: str, app_secret: str, encrypt_key: str = "", verification_token: str = ""):
        """
        Initialize Feishu Bot
        
        Args:
            app_id: Feishu App ID
            app_secret: Feishu App Secret
            encrypt_key: Event encryption key (optional, from Feishu console)
            verification_token: Event verification token (optional, from Feishu console)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.encrypt_key = encrypt_key
        self.verification_token = verification_token
        
        # Create client using builder pattern (for API calls)
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        # Create event dispatcher handler for processing events
        self.event_handler = EventDispatcherHandler.builder(
            encrypt_key=encrypt_key,
            verification_token=verification_token,
            level=lark.LogLevel.INFO
        ) \
        .register_p2_im_message_receive_v1(self._handle_message) \
        .register_p2_application_bot_menu_v6(self._handle_menu) \
        .build()
        
        # WebSocket client (using official SDK)
        self.ws_client = None
        
        logger.info("Feishu Bot client initialized")
    
    def _handle_message(self, event: P2ImMessageReceiveV1):
        """
        Handle message receive event
        
        Args:
            event: Message event data
        """
        try:
            message = event.event.message
            message_id = message.message_id
            message_type = message.message_type
            
            logger.info(f"Processing message - ID: {message_id}, Type: {message_type}")
            
            # Extract message content
            content_json = json.loads( message.content)
            logger.info(f"Message content JSON: {content_json['text']}")

        except Exception as e:
            logger.exception(f"Error handling message: {e}")
    
    def _handle_menu(self, event):
        """
        Handle bot menu event
        
        Args:
            event: Menu event data
        """
        logger.info(f"Received menu event: {event}")
    
    def reply_message(self, message_id: str, content: str, receive_id: str, receive_id_type: str = "chat_id"):
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
            
            # Implementation using SDK
            import json
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
            logger.info(f"App ID: {self.app_id}")
            
            # Create WebSocket client using official SDK
            # The SDK will automatically get the WebSocket URL from Feishu
            self.ws_client = WSClient(
                app_id=self.app_id,
                app_secret=self.app_secret,
                log_level=lark.LogLevel.INFO,
                event_handler=self.event_handler,
                auto_reconnect=True
            )
            
            logger.info("Feishu Bot WebSocket long connection client created")
            logger.info("Connecting to Feishu WebSocket server...")
            
            # Start the WebSocket connection
            # This will block until connection is established
            self.ws_client.start()
            
        except Exception as e:
            logger.exception(f"Error starting WebSocket long connection client: {e}")
            raise
    
    def stop(self):
        """Stop the WebSocket long connection client"""
        try:
            logger.info("Stopping Feishu Bot WebSocket long connection client...")
            if self.ws_client:
                # The SDK handles disconnection automatically
                pass
            logger.info("Feishu Bot WebSocket long connection client stopped")
        except Exception as e:
            logger.exception(f"Error stopping WebSocket long connection client: {e}")


def main():
    """Main entry point"""
    # Get App ID and App Secret from environment variables
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    encrypt_key = os.getenv('FEISHU_ENCRYPT_KEY', '')
    verification_token = os.getenv('FEISHU_VERIFICATION_TOKEN', '')
    
    if not app_id or not app_secret:
        logger.error("Please set FEISHU_APP_ID and FEISHU_APP_SECRET environment variables")
        logger.info("You can set them by:")
        logger.info("  export FEISHU_APP_ID='your_app_id'")
        logger.info("  export FEISHU_APP_SECRET='your_app_secret'")
        logger.info("")
        logger.info("Or create a .env file with:")
        logger.info("  FEISHU_APP_ID=your_app_id")
        logger.info("  FEISHU_APP_SECRET=your_app_secret")
        logger.info("  FEISHU_ENCRYPT_KEY=your_encrypt_key (optional)")
        logger.info("  FEISHU_VERIFICATION_TOKEN=your_verification_token (optional)")
        return
    
    # Create bot instance
    bot = FeishuBot(
        app_id=app_id,
        app_secret=app_secret,
        encrypt_key=encrypt_key,
        verification_token=verification_token
    )
    
    try:
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping bot...")
        bot.stop()
    except Exception as e:
        logger.exception(f"Error in main: {e}")
        bot.stop()


if __name__ == "__main__":
    main()
