import requests
import json
import os

def fetch_news(queries, api_key):
    all_articles = []
    for query in queries.split(', '):
        url = f'https://newsapi.org/v2/everything?q={query}&sortBy=relevancy&apiKey={api_key}'
        try:
            response = requests.get(url)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            if data['status'] == 'ok':
                for article in data['articles']:
                    all_articles.append({
                        'title': article.get('title'),
                        'description': article.get('description'),
                        'url': article.get('url'),
                        'source': article.get('source', {}).get('name'),
                        'publishedAt': article.get('publishedAt')
                    })
            else:
                print(f"Error fetching news for query '{query}': {data.get('message', 'Unknown error')}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed for query '{query}': {e}")
    return all_articles

if __name__ == '__main__':
    # This part is for direct testing, not for module execution
    # In actual use, parameters will be passed via runSovereignModule
    pass
