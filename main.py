"""
Main entry point for the backend application
"""
from occam.utils.logger import setup_logger
from occam.config import get_settings
from occam.services.message_processor import MessageProcessorService
from occam.bot.handlers import FeishuEventHandler
from occam.bot.client import FeishuBotClient
from loguru import logger


def main():
    """Main entry point"""
    # Setup logger
    setup_logger()
    
    try:
        # Load settings
        settings = get_settings()
        logger.info("Settings loaded successfully")
        
        # Initialize services
        message_processor = MessageProcessorService()
        event_handler = FeishuEventHandler(message_processor)
        
        # Create bot client
        bot = FeishuBotClient(
            settings=settings,
            event_handler=event_handler
        )
        
        # Start bot
        try:
            bot.start()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping bot...")
            bot.stop()
        except Exception as e:
            logger.exception(f"Error in main: {e}")
            bot.stop()
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.info("Please check your .env file or environment variables")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")


if __name__ == "__main__":
    main()
