import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

def scrape_url_to_markdown(url: str) -> str:
    """
    Fetches the URL, extracts the main article content (if possible),
    and converts it to clean Markdown.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Strip script and style elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.extract()
            
        # Try to find the main content block, or fallback to body
        main_content = soup.find("article") or soup.find("main") or soup.find("body")
        
        if not main_content:
            return "Could not extract content from URL. No body found."
            
        html_content = str(main_content)
        
        # Convert HTML to clean markdown
        markdown_content = md(
            html_content, 
            heading_style="ATX", 
            strip=["img", "a"], # Strip links/images to keep text clean, or keep them if preferred
        ).strip()
        
        # Basic cleanup of excessive newlines
        import re
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
        
        return f"# Extracted Content from {url}\n\n{markdown_content}"
        
    except Exception as e:
        return f"Error scraping {url}:\n\n{str(e)}"
