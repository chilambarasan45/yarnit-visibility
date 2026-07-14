"""
tests/test_openai.py

Run with: python -m tests.test_openai

Tests TWO things separately so we know exactly where a failure is:
  1. Basic connectivity/billing — plain chat.completions call, no tools.
     If this fails, it's an account/billing/key problem.
  2. The grounded web_search call — same one used in production
     (app/services/pipeline.py fire_openai). If (1) passes but (2)
     fails, it means your account/key works but doesn't have the
     web_search tool enabled yet for this model.
"""

import asyncio
from openai import AsyncOpenAI
from app.config import settings


async def test_basic_connectivity():
    print("\n--- TEST 1: Basic connectivity (no tools) ---")
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": "Say hello in one sentence"}],
            max_tokens=50,
        )
        print("✅ Basic call OK:", response.choices[0].message.content)
        return True
    except Exception as e:
        print(f"❌ Basic call FAILED: {e}")
        return False


async def test_grounded_web_search():
    print("\n--- TEST 2: Grounded web_search (Responses API) ---")
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = await client.responses.create(
            model=settings.OPENAI_MODEL,
            tools=[{
                "type": "web_search",
                "user_location": {
                    "type": "approximate",
                    "country": "IN",
                    "city": "Mumbai",
                    "region": "Maharashtra",
                },
            }],
            input="What is the capital of India?",
        )
        print("✅ Grounded call OK. Output:", getattr(response, "output_text", "")[:200])

        # Check if it actually grounded (used the tool) vs just answered from memory
        found_citation = False
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for content in getattr(item, "content", []) or []:
                    for annotation in getattr(content, "annotations", []) or []:
                        if getattr(annotation, "type", None) == "url_citation":
                            found_citation = True
                            print(f"   ✅ Found citation: {getattr(annotation, 'url', '')[:80]}")

        if not found_citation:
            print("   ⚠️  No citations found — model answered without grounding.")
        return True

    except Exception as e:
        print(f"❌ Grounded call FAILED: {e}")
        return False


async def main():
    print(f"Model configured: {settings.OPENAI_MODEL}")
    print(f"API key present: {'yes' if settings.OPENAI_API_KEY else 'NO - MISSING'}")

    basic_ok = await test_basic_connectivity()

    if not basic_ok:
        print("\n🛑 Basic connectivity failed — fix billing/API key before testing web_search.")
        return

    grounded_ok = await test_grounded_web_search()

    print("\n" + "=" * 50)
    if basic_ok and grounded_ok:
        print("✅ Both tests passed — OpenAI setup is fully working.")
    elif basic_ok and not grounded_ok:
        print("⚠️  Basic works, but web_search tool failed.")
        print("   Your account/billing is fine, but this specific model")
        print("   or your account tier may not have web_search access yet.")


if __name__ == "__main__":
    asyncio.run(main())