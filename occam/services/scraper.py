"""
Web scraping service using Playwright
Extracts main content from webpages and converts to Markdown format
Universal scraping solution with semantic understanding and state-aware loading
"""
import os
import re
import time
import json
import random
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from markdownify import markdownify as md
from loguru import logger
from bs4 import BeautifulSoup
import trafilatura
from playwright_stealth import Stealth
from openai import OpenAI

from occam.config import Settings, get_settings


class ScraperService:
    """Web scraping service for extracting webpage content with universal semantic extraction"""
    
    # Mainstream browser user agents (latest versions as of 2024)
    USER_AGENTS = [
        # Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
    
    def __init__(self, timeout: int = 90000, max_retries: int = 3, settings: Optional[Settings] = None):
        """
        Initialize scraper service
        
        Args:
            timeout: Timeout in milliseconds (default: 90 seconds)
            max_retries: Maximum number of retry attempts (default: 3)
            settings: Application settings (if None, will load from environment)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.settings = settings or get_settings()
        
        # Cookie storage directory
        backend_dir = Path(__file__).parent.parent.parent
        self.cookie_dir = backend_dir / ".cookies"
        self.cookie_dir.mkdir(exist_ok=True)
    
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
    
    def _get_random_user_agent(self) -> str:
        """
        Get a random user agent from the pool
        
        Returns:
            Random user agent string
        """
        return random.choice(self.USER_AGENTS)
    
    def _get_proxy_config(self) -> Optional[dict]:
        """
        Get proxy configuration from environment variable
        
        Returns:
            Proxy configuration dict for Playwright, or None if not configured
        """
        proxy_url = os.getenv('ALL_PROXY') or os.getenv('all_proxy')
        if not proxy_url:
            return None
        
        logger.info(f"Using proxy: {proxy_url}")
        return {"server": proxy_url}
    
    def _get_domain_from_url(self, url: str) -> str:
        """
        Extract domain from URL for cookie storage
        
        Args:
            url: URL string
        
        Returns:
            Domain string
        """
        parsed = urlparse(url)
        return parsed.netloc or parsed.hostname or "unknown"
    
    def _get_cookie_path(self, domain: str) -> Path:
        """
        Get cookie file path for a domain
        
        Args:
            domain: Domain name
        
        Returns:
            Path to cookie file
        """
        # Sanitize domain name for filename
        safe_domain = re.sub(r'[^\w\-.]', '_', domain)
        return self.cookie_dir / f"{safe_domain}.json"
    
    def _load_cookies(self, domain: str) -> list:
        """
        Load cookies for a domain from storage
        
        Args:
            domain: Domain name
        
        Returns:
            List of cookie dicts
        """
        cookie_path = self._get_cookie_path(domain)
        if not cookie_path.exists():
            return []
        
        try:
            with open(cookie_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                logger.info(f"Loaded {len(cookies)} cookies for {domain}")
                return cookies
        except Exception as e:
            logger.warning(f"Failed to load cookies for {domain}: {e}")
            return []
    
    def _save_cookies(self, context, domain: str):
        """
        Save cookies from context to storage
        
        Args:
            context: Playwright browser context
            domain: Domain name
        """
        try:
            cookies = context.cookies()
            if not cookies:
                return
            
            cookie_path = self._get_cookie_path(domain)
            with open(cookie_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(cookies)} cookies for {domain}")
        except Exception as e:
            logger.warning(f"Failed to save cookies for {domain}: {e}")
    
    def _adaptive_scroll(self, page):
        """
        Adaptive scrolling algorithm to load lazy-loaded content
        
        Args:
            page: Playwright page object
        """
        logger.info("Starting adaptive scroll to load lazy content")
        
        scroll_script = """
        async () => {
            const scrollHeight = () => document.body.scrollHeight;
            const innerHeight = () => window.innerHeight;
            const scrollY = () => window.scrollY || window.pageYOffset;
            
            let lastHeight = scrollHeight();
            let stableCount = 0;
            const maxStableCount = 3;
            const scrollStep = innerHeight();
            
            while (stableCount < maxStableCount) {
                // Scroll down
                window.scrollBy(0, scrollStep);
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // Check if height changed
                const currentHeight = scrollHeight();
                if (currentHeight === lastHeight) {
                    stableCount++;
                } else {
                    stableCount = 0;
                    lastHeight = currentHeight;
                }
            }
            
            // Scroll back to top
            window.scrollTo(0, 0);
            await new Promise(resolve => setTimeout(resolve, 300));
            
            return {
                finalHeight: scrollHeight(),
                scrollPosition: scrollY()
            };
        }
        """
        
        try:
            result = page.evaluate(scroll_script)
            logger.info(f"Adaptive scroll completed, final height: {result.get('finalHeight', 'unknown')}")
        except Exception as e:
            logger.warning(f"Adaptive scroll failed: {e}")
    
    def _preprocess_html(self, html: str) -> str:
        """
        Preprocess HTML by removing noise and preserving semantic tags
        
        Args:
            html: Raw HTML string
        
        Returns:
            Cleaned HTML string
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove noise tags
        noise_tags = ['script', 'style', 'svg', 'path', 'nav', 'footer', 'header', 
                     'aside', 'advertisement', 'button', 'noscript', 'iframe', 
                     'embed', 'object', 'canvas']
        for tag in noise_tags:
            for element in soup.find_all(tag):
                element.decompose()
        
        # Remove elements with common noise classes/ids
        noise_selectors = [
            '[class*="ad"]', '[class*="advertisement"]', '[class*="sidebar"]',
            '[class*="menu"]', '[class*="navigation"]', '[id*="ad"]',
            '[id*="sidebar"]', '[id*="menu"]', '[id*="nav"]'
        ]
        for selector in noise_selectors:
            try:
                for element in soup.select(selector):
                    # Be careful not to remove main content
                    if element.name not in ['article', 'main', 'body']:
                        element.decompose()
            except Exception:
                continue
        
        # Preserve semantic tags: article, h1-h6, p, img, table, li, ul, ol, blockquote, code, pre, a, strong, em, etc.
        # BeautifulSoup already preserves these by default
        
        return str(soup)
    
    def _extract_with_llm(self, html: str, url: str = "") -> Optional[str]:
        """
        Extract content using LLM semantic understanding
        
        Args:
            html: HTML string (raw HTML from page)
            url: Original URL (optional, for trafilatura)
        
        Returns:
            Markdown content string, or None if extraction fails
        """
        if not self.settings.llm_base_url or not self.settings.llm_api_key:
            logger.warning("LLM not configured, skipping AI extraction")
            return None
        
        try:
            logger.info("Attempting AI semantic extraction")
            
            # Use trafilatura to extract main content first (better than our simple preprocessing)
            # This removes noise more effectively and saves tokens
            content_for_llm = None
            is_xml_format = False
            try:
                extracted_xml = trafilatura.extract(html, output_format='xml', url=url)
                if extracted_xml and len(extracted_xml) > 100:
                    # Use trafilatura-extracted XML content for LLM
                    content_for_llm = extracted_xml
                    is_xml_format = True
                    logger.info(f"Using trafilatura-extracted content for LLM, length: {len(content_for_llm)} characters")
            except Exception as e:
                logger.warning(f"Trafilatura preprocessing failed: {e}, using fallback preprocessing")
            
            # Fallback to our preprocessing if trafilatura failed or returned insufficient content
            if not content_for_llm:
                content_for_llm = self._preprocess_html(html)
                logger.info(f"Using preprocessed HTML, length: {len(content_for_llm)} characters")
            
            # Truncate if still too long (LLM token limits)
            max_content_length = 50000  # Conservative limit
            if len(content_for_llm) > max_content_length:
                logger.warning(f"Content still too long after preprocessing ({len(content_for_llm)} chars), truncating to {max_content_length}")
                content_for_llm = content_for_llm[:max_content_length] + "...[truncated]"
            
            client = OpenAI(
                base_url=self.settings.llm_base_url,
                api_key=self.settings.llm_api_key,
                timeout=30.0,  # 30 second timeout for extraction
            )
            
            # Adjust prompt based on content format (XML from trafilatura or HTML)
            content_type = "XML" if is_xml_format else "HTML"
            prompt = f"""你是一个专业的网页内容提取助手。请从以下 {content_type} 源码中提取正文内容，保留 Markdown 格式，忽略广告和导航栏。直接输出 Markdown，不要添加任何解释。

{content_type} 源码：
{content_for_llm}

请提取正文内容并输出为 Markdown 格式："""
            
            response = client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的网页内容提取助手，擅长从 HTML 中提取正文并转换为 Markdown 格式。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=min(self.settings.llm_max_tokens, 16384),  # Limit output tokens
            )
            
            markdown = response.choices[0].message.content.strip()
            logger.info(f"AI extraction successful, length: {len(markdown)} characters")
            return markdown
            
        except Exception as e:
            logger.warning(f"AI extraction failed: {e}")
            return None
    
    def _extract_with_trafilatura(self, html: str, url: str) -> Optional[str]:
        """
        Extract content using trafilatura library
        
        Args:
            html: HTML string
            url: Original URL
        
        Returns:
            Markdown content string, or None if extraction fails
        """
        try:
            logger.info("Attempting trafilatura extraction")
            markdown = trafilatura.extract(html, output_format='markdown', url=url)
            if markdown and len(markdown) > 100:
                logger.info(f"Trafilatura extraction successful, length: {len(markdown)} characters")
                return markdown
            else:
                logger.warning("Trafilatura extraction returned empty or too short content")
                return None
        except Exception as e:
            logger.warning(f"Trafilatura extraction failed: {e}")
            return None
    
    def _extract_with_fallback(self, page, url: str) -> str:
        """
        Extract content with multi-level fallback strategy
        
        Priority:
        1. AI semantic extraction
        2. Trafilatura extraction
        3. Body conversion (fallback)
        
        Args:
            page: Playwright page object
            url: URL being fetched
        
        Returns:
            Markdown formatted content string
        """
        # Get full HTML
        body = page.query_selector("body")
        if not body:
            raise Exception("Could not extract content from page: body not found")
        
        raw_html = body.inner_html()
        
        # Try AI extraction first (pass raw HTML and URL for trafilatura preprocessing)
        markdown = self._extract_with_llm(raw_html, url)
        if markdown and len(markdown) > 100:
            logger.info("Using AI-extracted content")
            return markdown
        
        # Fallback to trafilatura (markdown format)
        markdown = self._extract_with_trafilatura(raw_html, url)
        if markdown and len(markdown) > 100:
            logger.info("Using trafilatura-extracted content")
            return markdown
        
        # Final fallback: preprocess and convert body to markdown
        logger.warning("Using body fallback conversion")
        cleaned_html = self._preprocess_html(raw_html)
        markdown = md(
            cleaned_html,
            heading_style="ATX",
            bullets="-",
            strip=['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement', 'button']
        )
        
        if not markdown or len(markdown) < 50:
            raise Exception("All extraction methods failed or returned insufficient content")
        
        return markdown
    
    def _fetch_with_playwright(self, url: str) -> str:
        """
        Internal function to fetch webpage with Playwright
        
        Args:
            url: URL to fetch
        
        Returns:
            Markdown formatted content string
        """
        domain = self._get_domain_from_url(url)
        
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
            
            # Get proxy configuration
            proxy_config = self._get_proxy_config()
            
            # Get random user agent
            user_agent = self._get_random_user_agent()
            
            # Create context with realistic browser headers
            context_options = {
                "user_agent": user_agent,
                "viewport": {"width": 1920, "height": 1080},
                "locale": "zh-CN",
                "timezone_id": "Asia/Shanghai",
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                }
            }
            
            # Add proxy configuration if available
            if proxy_config:
                context_options["proxy"] = proxy_config
            
            context = browser.new_context(**context_options)
            
            # Apply stealth plugin
            try:
                stealth = Stealth()
                stealth.apply_stealth_sync(context)
                logger.info("Applied playwright-stealth plugin")
            except Exception as e:
                logger.warning(f"Failed to apply stealth plugin: {e}")
            
            # Load cookies
            cookies = self._load_cookies(domain)
            if cookies:
                context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies for {domain}")
            
            page = context.new_page()
            
            # Navigate to URL with network idle detection
            try:
                page.goto(url, wait_until="networkidle", timeout=self.timeout)
                logger.info("Page loaded with networkidle")
            except PlaywrightTimeoutError:
                logger.warning("networkidle timeout, trying with load state")
                try:
                    page.goto(url, wait_until="load", timeout=self.timeout)
                    logger.info("Page loaded with load state")
                except PlaywrightTimeoutError:
                    logger.warning("load timeout, trying with domcontentloaded")
                    page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                    logger.info("Page loaded with domcontentloaded")
            
            # Adaptive scrolling for lazy-loaded content
            self._adaptive_scroll(page)
            
            # Wait for network to be idle after scrolling
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                logger.warning("Network idle wait timeout after scrolling, continuing")
            
            # Extract content with fallback strategy
            markdown_content = self._extract_with_fallback(page, url)
            
            # Clean up markdown
            markdown_content = self._clean_markdown(markdown_content)
            
            # Save cookies before closing
            self._save_cookies(context, domain)
            
            browser.close()
            
            logger.info(f"Successfully extracted content, length: {len(markdown_content)} characters")
            return markdown_content
    
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
