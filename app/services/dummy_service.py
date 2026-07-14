import time
import random

# ══════════════════════════════════════════════
# DUMMY DATA — mimics real pipeline output
# ──────────────────────────────────────────────
# Used only while DEMO_MODE = True in config.py
# Every function here has the exact same
# input/output shape as its real counterpart in
# serp_service.py / claude_service.py, so swapping
# them out later requires zero changes to brands.py
# ══════════════════════════════════════════════

def dummy_crawl_brand(domain: str) -> list[dict]:
    print(f"🧪 [DEMO] Pretending to crawl {domain}...")
    time.sleep(0.5)
    return [
        {"url": f"https://{domain}/product/sneaker-1", "title": "Comfort Walk Sneaker", "text": "Our sneakers offer arch support and wide fit for flat feet. Priced under 3000 rupees."},
        {"url": f"https://{domain}/product/sneaker-2", "title": "Everyday Runner", "text": "Lightweight running shoe with cushioned sole, great for daily wear."},
        {"url": f"https://{domain}/faq", "title": "FAQ", "text": "Ships to India, UAE, and UK. Popular among students and young professionals."},
        {"url": f"https://{domain}/reviews", "title": "Customer Reviews", "text": "Customers say the shoes are durable and comfortable for long walks."},
        {"url": f"https://{domain}/about", "title": "About Us", "text": "A mid-market footwear brand competing with Bata and Liberty."},
    ]


def dummy_extract_bio(corpus: list[dict], domain: str) -> dict:
    print(f"🧪 [DEMO] Pretending to extract BIO for {domain}...")
    time.sleep(0.5)
    return {
        "brand_name": domain.split(".")[0].capitalize(),
        "domain": domain,
        "product_categories": ["sneakers", "running shoes"],
        "product_attributes": ["arch support", "wide fit", "cushioned sole"],
        "use_cases": ["daily wear", "walking", "running"],
        "target_personas": ["students", "young professionals"],
        "price_positioning": "mid-market",
        "competitor_signals": ["Bata", "Liberty"],
        "geo_markets": ["IN", "AE", "GB"],
        "category_keywords": ["comfortable sneakers", "arch support shoes"],
        "review_signals": ["durable", "comfortable for long walks"],
        "confidence_flags": [],
        "bio_version": "1.0-demo",
    }


def dummy_enrich_from_serp(bio: dict) -> list[str]:
    print(f"🧪 [DEMO] Pretending to fetch PAA + Autocomplete signals...")
    time.sleep(0.5)
    return [
        "what is the best sneaker for flat feet",
        "how to choose running shoes for daily wear",
        "best affordable sneakers for students",
        "comfortable shoes for walking all day",
        "which shoe brand has good arch support",
    ]


def dummy_construct_prompts(bio: dict, raw_signals: list[str]) -> list[dict]:
    print(f"🧪 [DEMO] Pretending to construct prompts via Claude...")
    time.sleep(0.5)
    brand = bio.get("brand_name", "Brand")
    prompts = []
    clusters = ["informational", "comparative", "transactional", "experiential"]
    for i, signal in enumerate(raw_signals):
        prompts.append({
            "prompt_text": signal.capitalize() + "?",
            "intent_cluster": clusters[i % len(clusters)],
            "prompt_type": "category",
            "source_signal": signal,
        })
    # add one branded prompt for realism
    prompts.append({
        "prompt_text": f"Is {brand} a good brand for flat feet support?",
        "intent_cluster": "comparative",
        "prompt_type": "branded",
        "source_signal": "manual",
    })
    return prompts


def dummy_fire_prompts(prompts: list[dict], geos: list[str] = ["IN"]) -> list[dict]:
    print(f"🧪 [DEMO] Pretending to fire {len(prompts)} prompts at Gemini + Perplexity...")
    time.sleep(0.5)
    responses = []
    engines = ["gemini", "perplexity"]
    sample_answers = [
        "For flat feet, I'd recommend Bata Comfort or Liberty Force 10 for good arch support.",
        "Some popular options include Nike, Adidas, and local brands like Bata for everyday wear.",
        "This brand offers wide-fit sneakers with cushioned soles, well suited for long walks.",
    ]
    for prompt in prompts:
        for engine in engines:
            for geo in geos:
                responses.append({
                    "prompt_id": prompt["prompt_text"][:20],
                    "prompt_text": prompt["prompt_text"],
                    "intent_cluster": prompt["intent_cluster"],
                    "prompt_type": prompt["prompt_type"],
                    "engine": engine,
                    "geo": geo,
                    "raw_response": random.choice(sample_answers),
                })
    return responses


def dummy_parse_response(raw_response: str, brand_name: str) -> dict:
    mentioned = brand_name.lower() in raw_response.lower() or random.random() < 0.3
    return {
        "brand_mentioned": mentioned,
        "brand_cited": False,
        "mention_form": "exact" if mentioned else "none",
        "mention_position": 1 if mentioned else None,
        "sentiment": "positive" if mentioned else "not_applicable",
        "competing_brands": [
            {"brand_name": "Bata", "mention_position": 1, "cited": False},
            {"brand_name": "Liberty", "mention_position": 2, "cited": False},
        ],
    }