import requests
import asyncio
import google.generativeai as genai
from openai import AsyncOpenAI
from app.config import settings


def test_serp():
    print("\n--- Testing SerpAPI ---")
    params = {
        "engine":  "google",
        "q":       "site:mochi.in",
        "num":     5,
        "api_key": settings.SERP_API_KEY,
    }
    response = requests.get("https://serpapi.com/search", params=params, timeout=30)
    data     = response.json()
    results  = data.get("organic_results", [])
    print(f"SerpAPI OK — found {len(results)} results")
    for r in results[:3]:
        print(f"  • {r['link']}")


def test_gemini():
    print("\n--- Testing Gemini ---")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model    = genai.GenerativeModel(settings.GEMINI_MODEL)
    response = model.generate_content("Say hello in one sentence")
    print(f"Gemini OK — {response.text}")


async def test_openai():
    print("\n--- Testing OpenAI ---")
    client   = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": "Say hello in one sentence"}],
        max_tokens=50,
    )
    print(f"OpenAI OK — {response.choices[0].message.content}")


if __name__ == "__main__":
    test_serp()
    test_gemini()
    asyncio.run(test_openai())