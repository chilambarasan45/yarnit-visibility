"""
Mock pipeline test — runs the full pipeline logic
using fake data instead of real API calls.
Used to verify all stages connect correctly
before API keys arrive.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal, Brand, Client, Prompt, Run, Response, Base, engine

# ══════════════════════════════════════════════
# MOCK DATA — simulates what real APIs return
# ══════════════════════════════════════════════

MOCK_CORPUS = [
    {
        "url":   "https://mochi.in/collections/sneakers",
        "title": "Sneakers — Mochi Shoes",
        "text":  "Mochi offers premium sneakers for men and women. Our collection includes "
                 "casual sneakers, sports sneakers, and formal sneakers. Price range 999 to 4999. "
                 "Features: cushioned sole, wide fit, flat foot support. "
                 "Shop online or visit 500+ stores across India.",
    },
    {
        "url":   "https://mochi.in/pages/about",
        "title": "About Mochi",
        "text":  "Mochi is India's leading footwear brand. Founded in 1999, we serve "
                 "customers across India, UAE, and UK. Competitors include Bata, Metro Shoes, "
                 "and Clarks. We offer 30-day returns and free shipping above 999 rupees.",
    },
]

MOCK_BIO = {
    "brand_name":        "Mochi Shoes",
    "domain":            "mochi.in",
    "product_categories": ["sneakers", "formal shoes", "sandals", "boots"],
    "product_attributes": ["flat foot support", "wide fit", "cushioned sole", "lightweight"],
    "use_cases":          ["office wear", "casual outings", "sports", "travel"],
    "target_personas":    ["working professionals", "college students", "fitness enthusiasts"],
    "price_positioning":  "mid-market",
    "competitor_signals": ["Bata", "Metro Shoes", "Clarks", "Woodland"],
    "geo_markets":        ["IN", "AE", "GB"],
    "category_keywords":  ["footwear India", "comfortable shoes", "affordable sneakers"],
    "review_signals":     ["great comfort", "good value", "stylish design"],
    "confidence_flags":   [],
    "bio_version":        "1.0",
}

MOCK_SIGNALS = [
    "best sneakers for flat feet under 3000",
    "which shoe brand is best for office wear India",
    "comfortable shoes for long walks",
    "Mochi vs Bata which is better",
    "affordable formal shoes online India",
]

MOCK_PROMPTS = [
    {
        "prompt_text":    "What are the best sneakers for flat feet under 3000 rupees in India?",
        "intent_cluster": "transactional",
        "prompt_type":    "category",
        "source_signal":  "best sneakers for flat feet under 3000",
    },
    {
        "prompt_text":    "Which shoe brand is best for office wear in India?",
        "intent_cluster": "comparative",
        "prompt_type":    "category",
        "source_signal":  "which shoe brand is best for office wear India",
    },
    {
        "prompt_text":    "Are Mochi shoes good for long walks?",
        "intent_cluster": "informational",
        "prompt_type":    "branded",
        "source_signal":  "comfortable shoes for long walks",
    },
    {
        "prompt_text":    "Mochi vs Bata — which is better for everyday wear?",
        "intent_cluster": "comparative",
        "prompt_type":    "branded",
        "source_signal":  "Mochi vs Bata which is better",
    },
    {
        "prompt_text":    "Where can I buy affordable formal shoes online in India?",
        "intent_cluster": "transactional",
        "prompt_type":    "category",
        "source_signal":  "affordable formal shoes online India",
    },
]

MOCK_RESPONSES = [
    {
        "engine": "gemini",
        "geo":    "IN",
        "raw":    "For flat feet under 3000 rupees, I'd recommend Mochi Shoes which offers "
                  "great arch support and cushioning. Bata is also a good option.",
        "parsed": {
            "brand_mentioned":  True,
            "brand_cited":      False,
            "mention_form":     "exact",
            "mention_position": 1,
            "sentiment":        "positive",
            "competing_brands": [{"brand_name": "Bata", "mention_position": 2, "cited": False}],
        },
    },
    {
        "engine": "perplexity",
        "geo":    "IN",
        "raw":    "The best shoe brands for office wear in India include Bata, Metro Shoes, "
                  "and Woodland. These brands offer a good range of formal footwear.",
        "parsed": {
            "brand_mentioned":  False,
            "brand_cited":      False,
            "mention_form":     "none",
            "mention_position": None,
            "sentiment":        "not_applicable",
            "competing_brands": [
                {"brand_name": "Bata",        "mention_position": 1, "cited": False},
                {"brand_name": "Metro Shoes", "mention_position": 2, "cited": False},
                {"brand_name": "Woodland",    "mention_position": 3, "cited": False},
            ],
        },
    },
    {
        "engine": "gemini",
        "geo":    "AE",
        "raw":    "Mochi Shoes is a popular Indian footwear brand known for comfort. "
                  "They have stores across UAE as well.",
        "parsed": {
            "brand_mentioned":  True,
            "brand_cited":      False,
            "mention_form":     "exact",
            "mention_position": 1,
            "sentiment":        "positive",
            "competing_brands": [],
        },
    },
    {
        "engine": "perplexity",
        "geo":    "GB",
        "raw":    "For affordable formal shoes online, Clarks and Woodland are good options "
                  "available in the UK.",
        "parsed": {
            "brand_mentioned":  False,
            "brand_cited":      False,
            "mention_form":     "none",
            "mention_position": None,
            "sentiment":        "not_applicable",
            "competing_brands": [
                {"brand_name": "Clarks",   "mention_position": 1, "cited": False},
                {"brand_name": "Woodland", "mention_position": 2, "cited": False},
            ],
        },
    },
    {
        "engine": "gemini",
        "geo":    "IN",
        "raw":    "Mochi vs Bata — both are great Indian footwear brands. Mochi has a more "
                  "modern and stylish range while Bata is more traditional.",
        "parsed": {
            "brand_mentioned":  True,
            "brand_cited":      False,
            "mention_form":     "exact",
            "mention_position": 1,
            "sentiment":        "positive",
            "competing_brands": [{"brand_name": "Bata", "mention_position": 2, "cited": False}],
        },
    },
]


# ══════════════════════════════════════════════
# RUN MOCK PIPELINE
# ══════════════════════════════════════════════

def run_mock_pipeline():
    print("\n🚀 Running MOCK pipeline for Mochi Shoes")
    print("=" * 55)

    db = SessionLocal()

    try:
        # Step 1 — Create client
        print("\n📋 Step 1: Creating client...")
        client = Client(name="Landmark Group (Mock)")
        db.add(client)
        db.commit()
        db.refresh(client)
        print(f"   ✅ Client created: {client.name} ({client.id})")

        # Step 2 — Create brand
        print("\n🏷️  Step 2: Creating brand...")
        brand = Brand(
            client_id   = client.id,
            name        = "Mochi Shoes",
            domain      = "mochi.in",
            bio         = MOCK_BIO,
            active_geos = ["IN", "AE", "GB"],
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)
        print(f"   ✅ Brand created: {brand.name} ({brand.id})")

        # Step 3 — Create run
        print("\n🔄 Step 3: Creating run record...")
        from datetime import datetime
        run = Run(
            brand_id     = brand.id,
            triggered_by = "mock_test",
            status       = "running",
            started_at   = datetime.utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        print(f"   ✅ Run created: {run.id}")

        # Step 4 — Save prompts
        print("\n📝 Step 4: Saving prompts...")
        saved_prompts = []
        for p in MOCK_PROMPTS:
            prompt = Prompt(
                brand_id       = brand.id,
                prompt_text    = p["prompt_text"],
                intent_cluster = p["intent_cluster"],
                prompt_type    = p["prompt_type"],
                source_signals = [p["source_signal"]],
            )
            db.add(prompt)
            saved_prompts.append(prompt)
        db.commit()
        print(f"   ✅ {len(saved_prompts)} prompts saved")

        # Step 5 — Save mock responses
        print("\n💾 Step 5: Saving mock responses...")
        for i, (prompt, mock_resp) in enumerate(zip(saved_prompts, MOCK_RESPONSES)):
            response = Response(
                run_id           = run.id,
                brand_id         = brand.id,
                prompt_id        = prompt.id,
                prompt_text      = prompt.prompt_text,
                intent_cluster   = prompt.intent_cluster,
                prompt_type      = prompt.prompt_type,
                engine           = mock_resp["engine"],
                geo              = mock_resp["geo"],
                raw_response     = mock_resp["raw"],
                brand_mentioned  = mock_resp["parsed"]["brand_mentioned"],
                brand_cited      = mock_resp["parsed"]["brand_cited"],
                mention_form     = mock_resp["parsed"]["mention_form"],
                mention_position = mock_resp["parsed"]["mention_position"],
                sentiment        = mock_resp["parsed"]["sentiment"],
                competing_brands = mock_resp["parsed"]["competing_brands"],
                parsing_status   = "complete",
            )
            db.add(response)

        db.commit()
        print(f"   ✅ {len(MOCK_RESPONSES)} responses saved")

        # Step 6 — Update run status
        run.status        = "complete"
        run.completed_at  = datetime.utcnow()
        run.total_calls   = len(MOCK_RESPONSES)
        run.success_count = len(MOCK_RESPONSES)
        run.failed_count  = 0
        db.commit()

        print(f"\n🎉 Mock pipeline complete!")
        print(f"   Brand ID: {brand.id}")
        print(f"\n👉 Now go to http://localhost:3000")
        print(f"   Click 'View Dashboard' for Mochi Shoes")
        print(f"   You should see REAL charts with mock data!")
        # Step 6 — Add historical mock responses
        # (simulates data from previous months for trend chart)
        print("\n📅 Step 6: Adding historical mock data for trend chart...")

        from datetime import datetime, timedelta

        historical_data = [
            # 3 months ago — low visibility
            {"months_ago": 3, "mentioned": 1, "total": 5},
            # 2 months ago — improving
            {"months_ago": 2, "mentioned": 2, "total": 5},
            # 1 month ago — better
            {"months_ago": 1, "mentioned": 2, "total": 5},
            # This month — current (already added above)
        ]

        for hist in historical_data:
            # Create a historical run
            hist_date = datetime.utcnow() - timedelta(days=hist["months_ago"] * 30)

            hist_run = Run(
                brand_id     = brand.id,
                triggered_by = "mock_historical",
                status       = "complete",
                started_at   = hist_date,
                completed_at = hist_date,
                total_calls  = hist["total"],
                success_count = hist["total"],
                failed_count  = 0,
            )
            db.add(hist_run)
            db.commit()
            db.refresh(hist_run)

            # Add mock responses for this historical run
            for j in range(hist["total"]):
                is_mentioned = j < hist["mentioned"]
                hist_response = Response(
                    run_id           = hist_run.id,
                    brand_id         = brand.id,
                    prompt_id        = saved_prompts[j % len(saved_prompts)].id,
                    prompt_text      = saved_prompts[j % len(saved_prompts)].prompt_text,
                    intent_cluster   = "informational",
                    prompt_type      = "category",
                    engine           = "gemini",
                    geo              = "IN",
                    run_date         = hist_date,
                    raw_response     = "mock historical response",
                    brand_mentioned  = is_mentioned,
                    brand_cited      = False,
                    mention_form     = "exact" if is_mentioned else "none",
                    mention_position = 1 if is_mentioned else None,
                    sentiment        = "positive" if is_mentioned else "not_applicable",
                    competing_brands = [],
                    parsing_status   = "complete",
                )
                db.add(hist_response)

        db.commit()
        print(f"   ✅ Historical data added for 3 previous months")
        return str(brand.id)
    

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    run_mock_pipeline()