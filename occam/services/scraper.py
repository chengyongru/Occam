"""
Web scraping service using Playwright
Extracts main content from webpages and converts to Markdown format
"""
import re
import time
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from markdownify import markdownify as md
from loguru import logger


class ScraperService:
    """Web scraping service for extracting webpage content"""
    
    def __init__(self, timeout: int = 90000, max_retries: int = 3):
        """
        Initialize scraper service
        
        Args:
            timeout: Timeout in milliseconds (default: 90 seconds)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.timeout = timeout
        self.max_retries = max_retries
    
    def fetch_content(self, url: str) -> str:
        """
        Fetch webpage content and convert to Markdown
        
        Args:
            url: URL to fetch
        
        Returns:
            Markdown formatted content string
        
        Raises:
            Exception: If scraping fails after all retries
        """
        logger.info(f"Fetching webpage content from: {url}")
        
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Attempt {attempt}/{self.max_retries}")
                return self._fetch_with_playwright(url)
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed: {str(e)}")
                if attempt < self.max_retries:
                    wait_time = attempt * 2  # Exponential backoff: 2s, 4s, 6s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
        
        raise Exception(f"Failed to fetch webpage after {self.max_retries} attempts: {url} - {str(last_error)}")
    
    def _fetch_with_playwright(self, url: str) -> str:
        """
        Internal function to fetch webpage with Playwright
        
        Args:
            url: URL to fetch
        
        Returns:
            Markdown formatted content string
        """
        with sync_playwright() as p:
            # Launch browser in headless mode with additional options
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            # Create context with realistic browser headers
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                }
            )
            page = context.new_page()
            
            # Navigate to URL with more lenient wait strategy
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            except PlaywrightTimeoutError:
                logger.warning("domcontentloaded timeout, trying with load state")
                page.goto(url, wait_until="load", timeout=self.timeout)
            
            # Wait a bit for dynamic content to load
            page.wait_for_timeout(2000)
            
            # Try to wait for main content selectors
            self._wait_for_content(page, url)
            
            # Extract main content with site-specific selectors
            main_content = self._extract_content(page, url)
            
            # Convert HTML to Markdown
            markdown_content = md(
                main_content,
                heading_style="ATX",
                bullets="-",
                strip=['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement', 'button']
            )
            
            # Clean up markdown
            markdown_content = self._clean_markdown(markdown_content)
            
            browser.close()
            
            logger.info(f"Successfully extracted content, length: {len(markdown_content)} characters")
            return markdown_content
    
    def _wait_for_content(self, page, url: str):
        """
        Wait for content to load with site-specific logic
        
        Args:
            page: Playwright page object
            url: URL being fetched
        """
        # Zhihu-specific selectors
        if "zhihu.com" in url:
            try:
                page.wait_for_selector(".RichContent-inner, .QuestionHeader-title, .ContentItem", timeout=10000)
                logger.info("Zhihu content detected, waiting for it to load")
                page.wait_for_timeout(3000)
            except Exception:
                logger.warning("Zhihu-specific selectors not found, continuing anyway")
        
        # Generic wait for common content selectors
        try:
            page.wait_for_selector("article, main, [role='main'], .content, .post, .article", timeout=5000)
        except Exception:
            logger.warning("Common content selectors not found, continuing anyway")
    
    def _extract_content(self, page, url: str) -> str:
        """
        Extract main content from page with site-specific logic
        
        Args:
            page: Playwright page object
            url: URL being fetched
        
        Returns:
            HTML content string
        """
        # Site-specific content extraction
        if "zhihu.com" in url:
            selectors = [
                ".RichContent-inner",
                ".ContentItem",
                ".QuestionHeader-title",
                "article",
            ]
            for selector in selectors:
                try:
                    element = page.query_selector(selector)
                    if element:
                        content = element.inner_html()
                        if len(content) > 100:
                            logger.info(f"Found Zhihu content using selector: {selector}")
                            return content
                except Exception:
                    continue
        
        # Generic content selectors
        content_selectors = [
            "article",
            "main",
            "[role='main']",
            ".content",
            ".post",
            ".article",
            ".entry-content",
            ".post-content",
            "#content",
            "#main",
            ".main-content",
        ]
        
        for selector in content_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    content = element.inner_html()
                    if len(content) > 100:
                        logger.info(f"Found content using selector: {selector}")
                        return content
            except Exception:
                continue
        
        # Fallback to body
        logger.warning("No main content selector found, using body")
        body = page.query_selector("body")
        if body:
            return body.inner_html()
        else:
            raise Exception("Could not extract content from page")
    
    def _clean_markdown(self, content: str) -> str:
        """
        Clean and normalize markdown content
        
        Args:
            content: Raw markdown content
        
        Returns:
            Cleaned markdown content
        """
        # Remove excessive blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Remove leading/trailing whitespace
        content = content.strip()
        
        # Remove common noise patterns
        content = re.sub(r'\[Skip to content\]', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[Skip to navigation\]', '', content, flags=re.IGNORECASE)
        
        return content

