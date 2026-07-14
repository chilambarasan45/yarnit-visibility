import requests
from app.config import settings

params = {
    "engine": "google",
    
    "q": "site:mochishoes.com",
    "num": 5,
    "api_key": settings.SERP_API_KEY,
}
response = requests.get("https://serpapi.com/search", params=params, timeout=30)
data = response.json()
results = data.get("organic_results", [])
print(f"SerpAPI OK - found {len(results)} results")
for r in results[:3]:
    print("  -", r["link"])

if len(results) == 0:
    print("\n--- FULL RESPONSE (for debugging) ---")
    print(data)