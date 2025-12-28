"""
Tool script to check Notion database schema
Run this script to see available properties in your Notion database
"""
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from occam.utils.logger import setup_logger
from occam.config import get_settings
from occam.services.notion_storage import NotionStorageService
from loguru import logger


def main():
    """Check and display Notion database schema"""
    setup_logger()
    
    try:
        settings = get_settings()
        logger.info("Loading Notion database schema...")
        
        storage = NotionStorageService(settings)
        schema = storage.get_database_schema()
        
        print("\n" + "=" * 60)
        print("Notion Database Schema")
        print("=" * 60)
        print(f"\nDatabase ID: {settings.notion_database_id}")
        print(f"\nAvailable Properties ({len(schema)}):\n")
        
        for prop_name, prop_info in schema.items():
            prop_type = prop_info.get('type', 'unknown')
            print(f"  • {prop_name}")
            print(f"    Type: {prop_type}")
            
            # Show additional info based on type
            if prop_type == 'title':
                print(f"    ⚠️  This is the Title property (required)")
            elif prop_type == 'rich_text':
                print(f"    📝 Rich Text property")
            elif prop_type == 'multi_select':
                print(f"    🏷️  Multi-select property")
            elif prop_type == 'number':
                print(f"    🔢 Number property")
            elif prop_type == 'url':
                print(f"    🔗 URL property")
            
            print()
        
        print("=" * 60)
        print("\nConfiguration Recommendations:\n")
        
        # Try to find title property
        title_prop = None
        for prop_name, prop_info in schema.items():
            if prop_info.get('type') == 'title':
                title_prop = prop_name
                break
        
        if title_prop:
            print(f"NOTION_PROPERTY_TITLE={title_prop}")
        else:
            print("⚠️  WARNING: No title property found! Database must have a title property.")
        
        # Suggest mappings for other properties
        print("\nFor other properties, configure based on your database schema:")
        print("  NOTION_PROPERTY_AI_SUMMARY=<your_property_name>")
        print("  NOTION_PROPERTY_CRITICAL_THINKING=<your_property_name>")
        print("  NOTION_PROPERTY_TAGS=<your_property_name>")
        print("  NOTION_PROPERTY_SCORE=<your_property_name>")
        print("  NOTION_PROPERTY_URL=<your_property_name>")
        print("\n" + "=" * 60)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print("\n❌ Configuration error. Please check your .env file.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Error: {e}")
        print(f"\n❌ Error: {e}")
        print("\n" + "=" * 60)
        print("故障排查步骤：")
        print("=" * 60)
        print("\n1. 检查 Integration 是否已连接到数据库：")
        print("   - 在 Notion 中打开您的数据库")
        print("   - 点击右上角的 '...' (三个点)")
        print("   - 选择 'Connections' → 添加您的 Integration")
        print("\n2. 检查 Integration 权限：")
        print("   - 访问 https://www.notion.so/my-integrations")
        print("   - 确保 Integration 有 'Read content' 权限")
        print("\n3. 验证数据库 ID：")
        print("   - 确保 .env 文件中的 NOTION_DATABASE_ID 正确")
        print("   - 数据库 ID 应该是 32 位字符（可能包含连字符）")
        print("\n4. 检查 Integration Token：")
        print("   - 确保 .env 文件中的 NOTION_TOKEN 正确")
        print("   - 新格式（2024年9月25日后）：以 'ntn_' 开头")
        print("   - 旧格式（仍有效）：以 'secret_' 开头")
        print("   - 从 Integration 设置页面复制完整的 token")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

