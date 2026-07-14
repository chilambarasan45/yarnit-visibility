import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import Brand, Prompt, Run, Response, get_db
from app.services.serp_service import crawl_brand, enrich_from_serp
from app.services.claude_service import extract_bio, construct_prompts, parse_response, find_brand_source_urls
from app.config import settings
import httpx
import json

# ══════════════════════════════════════════════
# STAGE 6 — LLM FIRING (grounded version)
# ──────────────────────────────────────────────
# Both functions now return a DICT, not a plain string:
#   {"raw_text": ..., "grounded": True/False, "source_urls": [...]}
# This carries proof of what was actually searched/cited, instead of
# throwing that information away.
# ══════════════════════════════════════════════

GEO_CONTEXT = {
    "IN": "Answer as if the user is in India.",
    "AE": "Answer as if the user is in UAE.",
    "GB": "Answer as if the user is in the United Kingdom.",
}

GEO_USER_LOCATION = {
    "IN": {"type": "approximate", "country": "IN", "city": "Mumbai", "region": "Maharashtra"},
    "AE": {"type": "approximate", "country": "AE", "city": "Dubai", "region": "Dubai"},
    "GB": {"type": "approximate", "country": "GB", "city": "London", "region": "England"},
}


async def fire_gemini(prompt_text: str, geo: str) -> dict:
    """Fire one prompt at Gemini WITH real Google Search grounding."""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        context = GEO_CONTEXT.get(geo, "")
        full_prompt = f"{context}\n\n{prompt_text}" if context else prompt_text

        grounding_tool = types.Tool(google_search=types.GoogleSearch())
        config = types.GenerateContentConfig(tools=[grounding_tool])

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=full_prompt,
            config=config,
        )

        result = {"raw_text": response.text or "", "grounded": False, "search_queries": [], "source_urls": [], "grounding_supports": []}

        candidate = response.candidates[0] if response.candidates else None
        gm = getattr(candidate, "grounding_metadata", None) if candidate else None

        if gm:
            result["grounded"] = True
            if getattr(gm, "web_search_queries", None):
                result["search_queries"] = list(gm.web_search_queries)
            if getattr(gm, "grounding_chunks", None):
                for chunk in gm.grounding_chunks:
                    if chunk.web:
                        result["source_urls"].append({"title": chunk.web.title, "uri": chunk.web.uri})
            # grounding_supports maps specific response TEXT SEGMENTS to
            # specific chunk indices -- this is what lets us find exactly
            # which citation backs the sentence that mentions the brand,
            # instead of guessing from domain/title alone.
            if getattr(gm, "grounding_supports", None):
                for support in gm.grounding_supports:
                    segment = getattr(support, "segment", None)
                    seg_text = getattr(segment, "text", "") if segment else ""
                    chunk_indices = list(getattr(support, "grounding_chunk_indices", []) or [])
                    if seg_text and chunk_indices:
                        result["grounding_supports"].append({
                            "text": seg_text,
                            "chunk_indices": chunk_indices,
                        })

        return result

    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return {"raw_text": "", "grounded": False, "search_queries": [], "source_urls": [], "grounding_supports": []}


async def fire_openai(prompt_text: str, geo: str) -> dict:
    """Fire one prompt at OpenAI WITH real web search grounding via the
    Responses API + user_location geo parameter."""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        location = GEO_USER_LOCATION.get(geo, {"type": "approximate"})

        response = await client.responses.create(
            model=settings.OPENAI_MODEL,
            tools=[{"type": "web_search", "user_location": location}],
            input=prompt_text,
        )

        result = {"raw_text": getattr(response, "output_text", "") or "", "grounded": False, "source_urls": []}

        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "message":
                for content in getattr(item, "content", []) or []:
                    for annotation in getattr(content, "annotations", []) or []:
                        if getattr(annotation, "type", None) == "url_citation":
                            result["grounded"] = True
                            start = getattr(annotation, "start_index", None)
                            end = getattr(annotation, "end_index", None)
                            covered_text = ""
                            if start is not None and end is not None and result["raw_text"]:
                                # Widen slightly -- citations usually sit right
                                # after/around the sentence they support, not
                                # necessarily wrapping the brand name exactly.
                                window_start = max(0, start - 120)
                                window_end = min(len(result["raw_text"]), end + 20)
                                covered_text = result["raw_text"][window_start:window_end]
                            result["source_urls"].append({
                                "title": getattr(annotation, "title", ""),
                                "url": getattr(annotation, "url", ""),
                                "start_index": start,
                                "end_index": end,
                                "_covered_text": covered_text,
                            })

        return result

    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return {"raw_text": "", "grounded": False, "source_urls": []}


# ══════════════════════════════════════════════
# FULL PIPELINE ORCHESTRATOR
# ──────────────────────────────────────────────
# Takes a brand domain
# Runs all 7 stages in order
# Stores everything in the database
# ══════════════════════════════════════════════

async def run_full_pipeline(brand_id: str, db: Session) -> dict:
    """
    Full 7-stage pipeline for one brand.
    Called when user triggers a new run.
    """

    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        return {"error": "Brand not found"}

    domain = brand.domain
    print(f"\n🚀 Starting full pipeline for: {domain}")

    run = Run(
        brand_id=brand_id,
        triggered_by="manual",
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        # ── Stage 1 + 2 — Crawl ──
        print("\n📡 Stage 1+2: Crawling brand pages...")
        corpus = crawl_brand(domain)
        if not corpus:
            run.status = "failed"
            db.commit()
            return {"error": "Crawl failed — not enough pages"}

        # ── Stage 3 — BIO Extraction ──
        print("\n🧠 Stage 3: Extracting BIO...")
        bio = extract_bio(corpus, domain)
        if not bio:
            run.status = "failed"
            db.commit()
            return {"error": "BIO extraction failed"}

        brand.bio            = bio
        brand.bio_updated_at = datetime.utcnow()
        db.commit()

        # ── Stage 4 — SERP Enrichment ──
        print("\n🔎 Stage 4: SERP enrichment...")
        raw_signals = enrich_from_serp(bio)
        if not raw_signals:
            run.status = "failed"
            db.commit()
            return {"error": "SERP enrichment failed"}

        # ── Stage 5 — Prompt Construction ──
        print("\n📝 Stage 5: Constructing prompts...")
        prompt_dicts = construct_prompts(bio, raw_signals)
        if not prompt_dicts:
            run.status = "failed"
            db.commit()
            return {"error": "Prompt construction failed"}

        saved_prompts = []
        for p in prompt_dicts:
            prompt = Prompt(
                brand_id       = brand_id,
                prompt_text    = p.get("prompt_text", ""),
                intent_cluster = p.get("intent_cluster", "informational"),
                prompt_type    = p.get("prompt_type", "category"),
                source_signals = [p.get("source_signal", "")],
            )
            db.add(prompt)
            saved_prompts.append(prompt)

        db.commit()
        print(f"✅ Saved {len(saved_prompts)} prompts to DB")

        # ── Stage 6 — LLM Firing ──
        print("\n🔥 Stage 6: Firing prompts at LLMs...")

        engines = ["gemini", "openai"]
        geos    = brand.active_geos or ["IN", "AE", "GB"]

        total_calls   = 0
        success_count = 0
        failed_count  = 0

        brand_name    = bio.get("brand_name", domain)
        brand_aliases = bio.get("aliases", [])

        for prompt in saved_prompts[:50]:   # cap at 200 prompts
            for engine in engines:
                for geo in geos:
                    total_calls += 1
                    if engine == "gemini":
                        fired = await fire_gemini(prompt.prompt_text, geo)
                    else:
                        fired = await fire_openai(prompt.prompt_text, geo)

                    raw = fired.get("raw_text", "")
                    if not raw:
                        failed_count += 1
                        continue

                    citation_urls = [
                        s.get("uri") or s.get("url", "")
                        for s in fired.get("source_urls", [])
                    ]
                    brand_source_urls = find_brand_source_urls(
                        fired.get("source_urls", []),
                        brand.domain,
                        brand_name,
                        brand_aliases=brand_aliases,
                        grounding_supports=fired.get("grounding_supports", []),
                    )

                    # ── Stage 7 — Parse the response ──
                    parsed = parse_response(raw, brand_name, brand_aliases)

                    response_record = Response(
                        run_id            = run.id,
                        brand_id          = brand_id,
                        prompt_id         = prompt.id,
                        prompt_text       = prompt.prompt_text,
                        intent_cluster    = prompt.intent_cluster,
                        prompt_type       = prompt.prompt_type,
                        engine            = engine,
                        geo               = geo,
                        raw_response      = raw,
                        citation_urls     = citation_urls,
                        brand_source_urls = brand_source_urls,
                        brand_mentioned   = parsed.get("brand_mentioned", False),
                        brand_cited       = parsed.get("brand_cited", False),
                        mention_form      = parsed.get("mention_form", "none"),
                        mention_position  = parsed.get("mention_position"),
                        sentiment         = parsed.get("sentiment", "not_applicable"),
                        competing_brands  = parsed.get("competing_brands", []),
                        parsing_status    = "complete",
                    )
                    db.add(response_record)
                    success_count += 1

                    if total_calls % 10 == 0:
                        db.commit()
                        print(f"  ✅ {total_calls} calls done...")

        db.commit()

        run.status        = "complete"
        run.completed_at  = datetime.utcnow()
        run.total_calls   = total_calls
        run.success_count = success_count
        run.failed_count  = failed_count
        db.commit()

        print(f"\n🎉 Pipeline complete!")
        print(f"   Total calls  : {total_calls}")
        print(f"   Successful   : {success_count}")
        print(f"   Failed       : {failed_count}")

        return {
            "status":        "complete",
            "run_id":        str(run.id),
            "total_calls":   total_calls,
            "success_count": success_count,
            "failed_count":  failed_count,
        }

    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        run.status = "failed"
        db.commit()
        return {"error": str(e)}