import requests
import json
import os
from datetime import datetime, timedelta

# --- Configuration ---
CONFIG_PATH = 'C:\\Users\\rlope\\.veritas\\config.json'
NEWS_API_KEY = None

try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
        NEWS_API_KEY = config.get('news_api_key') # FIXED: Changed to 'news_api_key'
except FileNotFoundError:
    print(f"Error: Config file not found at {CONFIG_PATH}")
    exit(1)
except json.JSONDecodeError:
    print(f"Error: Could not decode JSON from {CONFIG_PATH}")
    exit(1)

if not NEWS_API_KEY:
    print("Error: NewsAPI_key not found in config.json")
    exit(1)

NEWS_API_ENDPOINT = "https://newsapi.org/v2/everything"
SEARCH_QUERY = "Terafab" # Step 1: Defined search query

# --- Helper Functions ---
def fetch_news(query, api_key):
    print(f"Fetching news for: {query}")
    # Fetch news from the last 7 days (Terafab news doesn't publish daily)
    from_date = (datetime.now() - timedelta(days=7)).isoformat()
    params = {
        'q': query,
        'apiKey': api_key,
        'language': 'en',
        'sortBy': 'publishedAt',
        'from': from_date,
        'pageSize': 100 # Max articles per request
    }
    try:
        response = requests.get(NEWS_API_ENDPOINT, params=params, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors
        articles = response.json().get('articles', [])
        print(f"Found {len(articles)} articles.")
        return articles
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error fetching news: {e}")
        return []
    except requests.exceptions.Timeout:
        print("Timeout fetching news from NewsAPI.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return []

def summarize_article(article):
    # Simple summarization: use description, fallback to content or title
    summary = article.get('description')
    if not summary and article.get('content'):
        summary = article['content'].split('.')[0] + '.' if '.' in article['content'] else article['content']
    if not summary:
        summary = article.get('title', 'No summary available.')
    return summary

def store_in_vault(news_data):
    print("Storing news in Veritas Vault...")
    # The runSovereignModule tool will handle the actual vault interaction
    # For now, we'll just print what would be stored.
    # In a real scenario, this would call a specific vault module.
    
    # Simulating vault storage for now, as direct vault access isn't available here.
    # This would be replaced by a call to runSovereignModule('vault_ingest', news_data)
    
    # For demonstration, let's create a simple JSON file in .veritas
    vault_dir = 'C:\\Users\\rlope\\.veritas\\vault_ingest'
    os.makedirs(vault_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_path = os.path.join(vault_dir, f'terafab_news_{timestamp}.json')
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, indent=4)
        print(f"Simulated vault storage to: {file_path}")
        return True
    except IOError as e:
        print(f"Error simulating vault storage: {e}")
        return False

def main():
    articles = fetch_news(SEARCH_QUERY, NEWS_API_KEY)
    
    if not articles:
        print("No articles to process.")
        return

    processed_news = []
    for article in articles:
        summary = summarize_article(article)
        processed_news.append({
            'title': article.get('title'),
            'url': article.get('url'),
            'summary': summary,
            'publishedAt': article.get('publishedAt'),
            'source': article.get('source', {}).get('name')
        })
    
    if processed_news:
        store_in_vault(processed_news)
    else:
        print("No processed news to store.")

if __name__ == "__main__":
    main()