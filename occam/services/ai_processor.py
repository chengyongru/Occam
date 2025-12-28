"""
AI processing service using OpenAI-compatible API with Instructor
Extracts structured knowledge from raw content
"""
from typing import Optional
from openai import OpenAI
import instructor
from loguru import logger

from occam.models import KnowledgeEntry
from occam.config import Settings


class AIProcessorService:
    """AI processor service for extracting structured knowledge from content"""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize AI processor service
        
        Args:
            settings: Application settings (if None, will load from environment)
        """
        if settings is None:
            from occam.config import get_settings
            settings = get_settings()
        
        self.settings = settings
        self.base_url = settings.llm_base_url
        
        logger.info(f"Initializing AI processor with base_url: {self.base_url}")
        logger.info(f"Model: {settings.llm_model}")
        logger.info(f"API will be called at: {self.base_url}/chat/completions")
        
        # Create OpenAI client with custom base URL
        # Note: base_url should already include /v1 suffix from settings
        client = OpenAI(
            base_url=self.base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout,
        )
        
        # Patch client with Instructor for structured output
        self.client = instructor.patch(client)
    
    def process(self, raw_content: str, user_notes: Optional[str] = None, url: str = "") -> KnowledgeEntry:
        """
        Process raw content with AI to extract structured knowledge
        
        Args:
            raw_content: Raw markdown content from webpage
            user_notes: User's notes or thoughts (optional)
            url: Original article URL
        
        Returns:
            KnowledgeEntry with structured data
        """
        logger.info("Processing content with AI...")
        
        # Combine content and user notes
        full_content = raw_content
        if user_notes:
            full_content = f"{raw_content}\n\n---\n\n## 用户随笔\n\n{user_notes}"
        
        # Construct prompt for AI
        prompt = f"""请仔细阅读以下文章内容，并提取结构化信息。

文章内容：
{full_content}

请提取以下信息：
1. **标题 (title)**: 文章的标题
2. **核心观点 (ai_summary)**: 用一句话总结文章的核心观点或主要论点
3. **批判性思考 (critical_thinking)**: 提供3个批判性思考点或反直觉的洞察，每个思考点应该深入且有价值
4. **标签 (tags)**: 自动分类标签，如：认知科学、经济学、技术、哲学等，选择2-5个最相关的标签
5. **价值评分 (score)**: 对文章的价值进行评分（0-100分），考虑内容的深度、原创性、实用性等因素
6. **原始链接 (url)**: {url}
7. **完整内容 (page_content)**: 包含原始文章内容和用户随笔的完整 Markdown 内容

请确保：
- critical_thinking 必须恰好包含3个思考点
- tags 应该是相关的、有意义的分类标签
- score 应该客观反映文章的价值
- 所有字段都要填写完整
"""
        
        try:
            logger.info(f"Calling LLM API - Model: {self.settings.llm_model}, Base URL: {self.base_url}")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            # Use Instructor to get structured output
            # Note: DeepSeek doesn't support temperature, top_p, etc., but won't error
            # They just won't take effect. We keep them for compatibility.
            knowledge_entry = self.client.chat.completions.create(
                model=self.settings.llm_model,
                response_model=KnowledgeEntry,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位知识管理专家，擅长从文章中提取结构化信息和深度洞察。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.settings.llm_temperature,
                max_retries=self.settings.llm_max_retries,
                max_tokens=self.settings.llm_max_tokens,
            )
            
            logger.info(f"Successfully extracted knowledge entry: {knowledge_entry.title}")
            return knowledge_entry
            
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Error processing content with AI: {e}")
            
            # Provide more helpful error messages
            if "404" in error_msg or "not found" in error_msg.lower():
                error_hint = (
                    f"\n可能的原因：\n"
                    f"1. BASE_URL 配置不正确。当前值: {self.base_url}\n"
                    f"2. BASE_URL 必须包含 /v1 后缀，例如: https://api.openai-proxy.org/v1\n"
                    f"3. OpenAI 客户端会自动添加 /chat/completions，所以完整路径应该是: {self.base_url}/chat/completions\n"
                    f"4. 请检查 API 服务是否正常运行"
                )
                raise Exception(f"API 端点未找到 (404): {error_msg}{error_hint}")
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                raise Exception(f"API 认证失败 (401): 请检查 API_KEY 是否正确")
            elif "timeout" in error_msg.lower():
                raise Exception(f"API 请求超时: 请检查网络连接或增加超时时间")
            elif "max_tokens" in error_msg.lower() or "length limit" in error_msg.lower() or "incomplete" in error_msg.lower():
                error_hint = (
                    f"\n可能的原因：\n"
                    f"1. 输出内容过长，超过了 max_tokens 限制（当前: {self.settings.llm_max_tokens}）\n"
                    f"2. 文章内容太长，导致生成的 page_content 字段超过限制\n"
                    f"3. 解决方案：增加 LLM_MAX_TOKENS 环境变量值（例如: 65536）"
                )
                raise Exception(f"输出长度超限: {error_msg}{error_hint}")
            else:
                raise Exception(f"AI 处理失败: {error_msg}")
    
    def test_connection(self) -> bool:
        """
        Test API connection with a simple request
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Testing API connection to: {self.base_url}")
            
            test_response = self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=10,
            )
            
            logger.info("API connection test successful!")
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            logger.error(f"请检查：")
            logger.error(f"1. BASE_URL 是否正确（当前: {self.settings.llm_base_url}）")
            logger.error(f"2. BASE_URL 必须包含 /v1 后缀")
            logger.error(f"3. API_KEY 是否正确")
            logger.error(f"4. API 服务是否正常运行")
            return False

