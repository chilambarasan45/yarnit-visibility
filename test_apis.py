from app.config import settings

def test_openai():
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": "Reply with just: OK"}],
            max_tokens=5
        )
        print("✅ OpenAI working:", response.choices[0].message.content)
    except Exception as e:
        print("❌ OpenAI failed:", e)

def test_gemini():
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content("Reply with just: OK")
        print("✅ Gemini working:", response.text)
    except Exception as e:
        print("❌ Gemini failed:", e)

if __name__ == "__main__":
    test_openai()
    test_gemini()