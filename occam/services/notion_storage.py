"""
Notion API service for storing knowledge entries
Converts Pydantic models to Notion page format

Reference: https://developers.notion.com/reference
"""
from typing import List, Optional, Dict, Any
from notion_client import Client
from notion_client.errors import APIResponseError
from loguru import logger

from occam.models import KnowledgeEntry
from occam.config import Settings


class NotionStorageError(Exception):
    """Custom exception for Notion storage operations"""
    pass


class NotionStorageService:
    """Notion API service for creating pages in database"""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize Notion storage service
        
        Args:
            settings: Application settings (if None, will load from environment)
        
        Raises:
            NotionStorageError: If initialization fails
        """
        if settings is None:
            from occam.config import get_settings
            settings = get_settings()
        
        self.settings = settings
        
        try:
            self.client = Client(auth=settings.notion_token)
            self._database_schema: Optional[Dict[str, Any]] = None
            self._data_source_id: Optional[str] = None
            logger.info("Notion storage service initialized")
        except Exception as e:
            logger.exception(f"Failed to initialize Notion client: {e}")
            raise NotionStorageError(f"Failed to initialize Notion client: {str(e)}")
    
    def _get_data_source_id(self) -> str:
        """
        Get data source ID from database response
        According to Notion API 2025-09-03, properties are in data_source, not database
        
        Returns:
            Data source ID string
        
        Raises:
            NotionStorageError: If data source ID cannot be retrieved
        """
        if self._data_source_id is None:
            try:
                logger.info(f"Fetching data source ID for database: {self.settings.notion_database_id}")
                database = self.client.databases.retrieve(database_id=self.settings.notion_database_id)
                
                if not isinstance(database, dict):
                    raise NotionStorageError("Invalid database response format")
                
                # Check for data_sources in response (new API 2025-09-03 format)
                data_sources = database.get('data_sources', [])
                
                if data_sources and len(data_sources) > 0:
                    # Use the first data source (for single-source databases, there's only one)
                    self._data_source_id = data_sources[0].get('id')
                    if not self._data_source_id:
                        raise NotionStorageError("Data source ID not found in data_sources array")
                    logger.info(f"Found data source ID: {self._data_source_id}")
                else:
                    # Fallback: no data_sources means either old API or Integration not connected
                    logger.warning("No data_sources found in response")
                    # For backward compatibility, we'll try to use database_id
                    # But this won't work if Integration is not connected
                    raise NotionStorageError(
                        "No data_sources found in database response. "
                        "This usually means Integration is not connected to the database, "
                        "or you're using an older API version that doesn't support data sources."
                    )
                
            except APIResponseError as e:
                logger.exception(f"Notion API error fetching data source: {e}")
                raise NotionStorageError(f"Failed to fetch data source ID: {str(e)}")
            except Exception as e:
                logger.exception(f"Unexpected error fetching data source: {e}")
                raise NotionStorageError(f"Failed to fetch data source ID: {str(e)}")
        
        return self._data_source_id
    
    def get_database_schema(self) -> Dict[str, Any]:
        """
        Get database schema to understand available properties
        
        Returns:
            Dictionary mapping property names to their type information
        
        Raises:
            NotionStorageError: If schema retrieval fails
        """
        if self._database_schema is None:
            try:
                logger.info(f"Fetching database schema for: {self.settings.notion_database_id}")
                database = self.client.databases.retrieve(database_id=self.settings.notion_database_id)
                
                if not isinstance(database, dict):
                    raise NotionStorageError("Invalid database response format")
                
                # Log response keys for debugging
                logger.debug(f"Database response keys: {list(database.keys())}")
                
                # According to Notion API 2025-09-03, properties are in data_source, not database
                # First, check if we have data_sources (new API format)
                data_sources = database.get('data_sources', [])
                
                if data_sources and len(data_sources) > 0:
                    # New API format: properties are in data_source
                    data_source_id = data_sources[0].get('id')
                    if not data_source_id:
                        raise NotionStorageError("Data source ID not found in data_sources array")
                    
                    logger.info(f"Found data source ID: {data_source_id}, fetching properties...")
                    
                    # Store data source ID for later use
                    self._data_source_id = data_source_id
                    
                    # Try to get properties from data source
                    # Note: notion-client might not have data_sources.retrieve method yet
                    # So we'll use the request method directly
                    try:
                        # Use the client's internal request method to call data_sources API
                        data_source_response = self.client.request(
                            path=f"data_sources/{data_source_id}",
                            method="GET"
                        )
                        
                        if isinstance(data_source_response, dict):
                            self._database_schema = data_source_response.get('properties', {})
                            logger.info(f"Retrieved properties from data source: {len(self._database_schema)} properties")
                        else:
                            raise NotionStorageError("Invalid data source response format")
                            
                    except AttributeError:
                        # notion-client doesn't have request method, try alternative approach
                        logger.warning("notion-client doesn't support data_sources API directly")
                        logger.info("Trying to get properties from database response as fallback...")
                        # Fallback: try database properties (might work if Integration is connected)
                        self._database_schema = database.get('properties', {})
                    except Exception as e:
                        logger.warning(f"Could not fetch data source directly: {e}")
                        logger.info("Falling back to database properties...")
                        # Fallback: try database properties
                        self._database_schema = database.get('properties', {})
                else:
                    # Old API format or no data_sources: try to get properties from database directly
                    logger.info("No data_sources found, trying to get properties from database response...")
                    self._database_schema = database.get('properties', {})
                
                if not self._database_schema:
                    # Provide detailed error message
                    error_details = []
                    error_details.append("Database has no properties in response.")
                    error_details.append(f"Database ID: {self.settings.notion_database_id}")
                    error_details.append(f"Response keys: {list(database.keys())}")
                    
                    # Check if this might be a permission issue
                    if 'object' in database:
                        error_details.append(f"Object type: {database.get('object')}")
                    
                    error_details.append("\nPossible causes:")
                    error_details.append("1. Integration is not connected to the database")
                    error_details.append("   → Go to your Notion database page")
                    error_details.append("   → Click '...' (three dots) in the top right")
                    error_details.append("   → Select 'Connections' → Add your Integration")
                    error_details.append("2. Integration lacks 'Read content' permission")
                    error_details.append("   → Check Integration settings in Notion")
                    error_details.append("3. Database ID is incorrect")
                    error_details.append("   → Verify the database ID in your .env file")
                    
                    error_msg = "\n".join(error_details)
                    logger.error(error_msg)
                    raise NotionStorageError(error_msg)
                
                # Log available properties for debugging
                logger.info(f"Found {len(self._database_schema)} properties in database:")
                for prop_name, prop_info in self._database_schema.items():
                    if isinstance(prop_info, dict):
                        prop_type = prop_info.get('type', 'unknown')
                        logger.info(f"  - {prop_name}: {prop_type}")
                    else:
                        logger.warning(f"  - {prop_name}: invalid format")
                
            except APIResponseError as e:
                logger.exception(f"Notion API error fetching database schema: {e}")
                raise NotionStorageError(f"Failed to fetch database schema: {str(e)}")
            except Exception as e:
                logger.exception(f"Unexpected error fetching database schema: {e}")
                raise NotionStorageError(f"Failed to fetch database schema: {str(e)}")
        
        return self._database_schema
    
    def _get_property_type(self, property_name: str) -> Optional[str]:
        """
        Get the type of a property from database schema
        
        Args:
            property_name: Name of the property
        
        Returns:
            Property type or None if not found
        """
        schema = self.get_database_schema()
        prop_info = schema.get(property_name)
        if isinstance(prop_info, dict):
            return prop_info.get('type')
        return None
    
    def _find_property_name(self, configured_name: str) -> Optional[str]:
        """
        Find actual property name in database (case-insensitive)
        
        Args:
            configured_name: Configured property name
        
        Returns:
            Actual property name from database or None if not found
        """
        schema = self.get_database_schema()
        
        # Exact match
        if configured_name in schema:
            return configured_name
        
        # Case-insensitive match
        configured_lower = configured_name.lower().strip()
        for actual_name in schema.keys():
            if actual_name.lower().strip() == configured_lower:
                logger.info(f"Found case-insensitive match: '{configured_name}' -> '{actual_name}'")
                return actual_name
        
        return None
    
    def _build_title_property(self, property_name: str, value: str) -> Dict[str, Any]:
        """
        Build title property value
        
        Args:
            property_name: Property name
            value: Title value
        
        Returns:
            Property value dict
        """
        return {
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": value
                    }
                }
            ]
        }
    
    def _build_rich_text_property(self, property_name: str, value: str) -> Dict[str, Any]:
        """
        Build rich_text property value
        
        Args:
            property_name: Property name
            value: Text value
        
        Returns:
            Property value dict
        """
        if not value:
            return {"rich_text": []}
        
        return {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": value
                    }
                }
            ]
        }
    
    def _build_number_property(self, property_name: str, value: int) -> Dict[str, Any]:
        """
        Build number property value
        
        Args:
            property_name: Property name
            value: Number value
        
        Returns:
            Property value dict
        """
        return {
            "number": value
        }
    
    def _build_url_property(self, property_name: str, value: str) -> Dict[str, Any]:
        """
        Build URL property value
        
        Args:
            property_name: Property name
            value: URL value
        
        Returns:
            Property value dict
        """
        return {
            "url": value if value else None
        }
    
    def _build_multi_select_property(self, property_name: str, values: List[str]) -> Dict[str, Any]:
        """
        Build multi_select property value
        
        Args:
            property_name: Property name
            values: List of tag names
        
        Returns:
            Property value dict
        """
        if not values:
            return {"multi_select": []}
        
        return {
            "multi_select": [
                {"name": tag} for tag in values
            ]
        }
    
    def _build_property_value(
        self,
        property_name: str,
        property_type: str,
        value: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Build property value based on type
        
        Args:
            property_name: Property name
            property_type: Property type from schema
            value: Value to set
        
        Returns:
            Property value dict or None if type not supported
        """
        if property_type == "title":
            if not isinstance(value, str):
                logger.warning(f"Title property '{property_name}' expects string, got {type(value)}")
                value = str(value)
            return self._build_title_property(property_name, value)
        
        elif property_type == "rich_text":
            if not isinstance(value, str):
                logger.warning(f"Rich text property '{property_name}' expects string, got {type(value)}")
                value = str(value)
            return self._build_rich_text_property(property_name, value)
        
        elif property_type == "number":
            if not isinstance(value, (int, float)):
                logger.warning(f"Number property '{property_name}' expects number, got {type(value)}")
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    logger.error(f"Cannot convert '{value}' to number for property '{property_name}'")
                    return None
            return self._build_number_property(property_name, int(value))
        
        elif property_type == "url":
            if not isinstance(value, str):
                value = str(value)
            return self._build_url_property(property_name, value)
        
        elif property_type == "multi_select":
            if not isinstance(value, list):
                logger.warning(f"Multi-select property '{property_name}' expects list, got {type(value)}")
                return None
            return self._build_multi_select_property(property_name, value)
        
        else:
            logger.warning(f"Unsupported property type '{property_type}' for property '{property_name}'")
            return None
    
    def _build_properties(self, entry: KnowledgeEntry) -> Dict[str, Any]:
        """
        Build properties dictionary for Notion page
        
        Args:
            entry: KnowledgeEntry to convert
        
        Returns:
            Dictionary of property name -> property value
        
        Raises:
            NotionStorageError: If required properties are missing or invalid
        """
        properties = {}
        schema = self.get_database_schema()
        
        # Title property (required)
        prop_title = self.settings.notion_property_title
        if prop_title:
            actual_title_name = self._find_property_name(prop_title)
            if not actual_title_name:
                raise NotionStorageError(
                    f"Title property '{prop_title}' not found in database. "
                    f"Available properties: {list(schema.keys())}"
                )
            
            title_type = self._get_property_type(actual_title_name)
            if title_type != "title":
                raise NotionStorageError(
                    f"Property '{actual_title_name}' is not a title property (type: {title_type})"
                )
            
            title_value = self._build_property_value(actual_title_name, title_type, entry.title)
            if title_value:
                properties[actual_title_name] = title_value
        
        # AI Summary property
        prop_ai_summary = self.settings.notion_property_ai_summary
        if prop_ai_summary:
            actual_name = self._find_property_name(prop_ai_summary)
            if actual_name:
                prop_type = self._get_property_type(actual_name)
                if prop_type == "rich_text":
                    value = self._build_property_value(actual_name, prop_type, entry.ai_summary)
                    if value:
                        properties[actual_name] = value
                else:
                    logger.warning(f"Property '{actual_name}' is not rich_text type (type: {prop_type}), skipping")
        
        # Critical Thinking property
        prop_critical_thinking = self.settings.notion_property_critical_thinking
        if prop_critical_thinking:
            actual_name = self._find_property_name(prop_critical_thinking)
            if actual_name:
                prop_type = self._get_property_type(actual_name)
                if prop_type == "rich_text":
                    content = "\n".join([f"• {point}" for point in entry.critical_thinking])
                    value = self._build_property_value(actual_name, prop_type, content)
                    if value:
                        properties[actual_name] = value
                else:
                    logger.warning(f"Property '{actual_name}' is not rich_text type (type: {prop_type}), skipping")
        
        # Tags property
        prop_tags = self.settings.notion_property_tags
        if prop_tags and entry.tags:
            actual_name = self._find_property_name(prop_tags)
            if actual_name:
                prop_type = self._get_property_type(actual_name)
                if prop_type == "multi_select":
                    value = self._build_property_value(actual_name, prop_type, entry.tags)
                    if value:
                        properties[actual_name] = value
                else:
                    logger.warning(f"Property '{actual_name}' is not multi_select type (type: {prop_type}), skipping")
        
        # Score property
        prop_score = self.settings.notion_property_score
        if prop_score:
            actual_name = self._find_property_name(prop_score)
            if actual_name:
                prop_type = self._get_property_type(actual_name)
                if prop_type == "number":
                    value = self._build_property_value(actual_name, prop_type, entry.score)
                    if value:
                        properties[actual_name] = value
                else:
                    logger.warning(f"Property '{actual_name}' is not number type (type: {prop_type}), skipping")
        
        # URL property
        prop_url = self.settings.notion_property_url
        if prop_url:
            actual_name = self._find_property_name(prop_url)
            if actual_name:
                prop_type = self._get_property_type(actual_name)
                if prop_type == "url":
                    value = self._build_property_value(actual_name, prop_type, str(entry.url))
                    if value:
                        properties[actual_name] = value
                else:
                    logger.warning(f"Property '{actual_name}' is not url type (type: {prop_type}), skipping")
        
        if not properties:
            available_props = list(schema.keys())
            raise NotionStorageError(
                f"No valid properties could be built. "
                f"Available properties: {available_props}. "
                f"Please check your property name mappings in .env file."
            )
        
        logger.info(f"Built {len(properties)} properties for Notion page")
        return properties
    
    def create_page(self, entry: KnowledgeEntry) -> str:
        """
        Create a Notion page from KnowledgeEntry
        
        Args:
            entry: KnowledgeEntry to store
        
        Returns:
            URL of the created page
        
        Raises:
            NotionStorageError: If page creation fails
        """
        logger.info(f"Creating Notion page for: {entry.title}")
        
        try:
            # Build properties
            properties = self._build_properties(entry)
            
            # Convert Markdown content to Notion blocks
            content_blocks = self._markdown_to_blocks(entry.page_content)
            
            # Get data source ID (required for API 2025-09-03)
            # This ensures we have the data_source_id cached from schema retrieval
            data_source_id = self._get_data_source_id()
            
            # Create page using data_source_id (new API 2025-09-03 format)
            # According to the upgrade guide, we should use data_source_id instead of database_id
            logger.info(f"Creating page with data_source_id: {data_source_id}")
            response = self.client.pages.create(
                parent={"type": "data_source_id", "data_source_id": data_source_id},
                properties=properties,
                children=content_blocks
            )
            
            if not isinstance(response, dict) or "id" not in response:
                raise NotionStorageError("Invalid response from Notion API")
            
            # Get page URL
            page_id = response["id"]
            if not isinstance(page_id, str):
                raise NotionStorageError("Invalid page ID in response")
            
            # Format page ID for URL (remove hyphens)
            page_id_clean = page_id.replace('-', '')
            page_url = f"https://www.notion.so/{page_id_clean}"
            
            logger.info(f"Successfully created Notion page: {page_url}")
            return page_url
            
        except APIResponseError as e:
            error_msg = f"Notion API error: {str(e)}"
            logger.exception(error_msg)
            raise NotionStorageError(error_msg)
        except NotionStorageError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error creating Notion page: {str(e)}"
            logger.exception(error_msg)
            raise NotionStorageError(error_msg)
    
    def _markdown_to_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Convert Markdown content to Notion blocks
        
        Args:
            markdown: Markdown content string
        
        Returns:
            List of Notion block objects
        """
        if not markdown:
            return []
        
        blocks: List[Dict[str, Any]] = []
        lines = markdown.split('\n')
        current_paragraph: List[str] = []
        
        def flush_paragraph():
            """Flush current paragraph to blocks"""
            if current_paragraph:
                content = " ".join(current_paragraph)
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content
                                }
                            }
                        ]
                    }
                })
                current_paragraph.clear()
        
        for line in lines:
            line = line.strip()
            
            # Empty line - flush current paragraph
            if not line:
                flush_paragraph()
                continue
            
            # Headings
            if line.startswith('# '):
                flush_paragraph()
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": line[2:]
                                }
                            }
                        ]
                    }
                })
            elif line.startswith('## '):
                flush_paragraph()
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": line[3:]
                                }
                            }
                        ]
                    }
                })
            elif line.startswith('### '):
                flush_paragraph()
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": line[4:]
                                }
                            }
                        ]
                    }
                })
            # List items
            elif line.startswith('- ') or line.startswith('* '):
                flush_paragraph()
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": line[2:]
                                }
                            }
                        ]
                    }
                })
            else:
                # Regular text - accumulate into paragraph
                current_paragraph.append(line)
        
        # Flush remaining paragraph
        flush_paragraph()
        
        # If no blocks created, create at least one paragraph
        if not blocks:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": markdown
                            }
                        }
                    ]
                }
            })
        
        return blocks
