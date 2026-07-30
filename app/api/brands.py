from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from app.models.database import get_db, Client, Brand, Prompt, Run, Response
from app.services.pipeline import run_full_pipeline

router = APIRouter(prefix="/api", tags=["brands"])


# ══════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ══════════════════════════════════════════════

class CreateClientRequest(BaseModel):
    name: str

class CreateBrandRequest(BaseModel):
    client_id: str
    name:      str
    domain:    str
    geos:      Optional[list[str]] = ["IN", "AE", "GB"]

class RunPipelineRequest(BaseModel):
    brand_id: str


# ══════════════════════════════════════════════
# CLIENT ENDPOINTS
# ══════════════════════════════════════════════

@router.post("/clients")
def create_client(req: CreateClientRequest, db: Session = Depends(get_db)):
    """Create a new client (company using the platform)."""
    client = Client(name=req.name)
    db.add(client)
    db.commit()
    db.refresh(client)
    return {
        "id":         str(client.id),
        "name":       client.name,
        "created_at": client.created_at,
    }

@router.get("/clients")
def list_clients(db: Session = Depends(get_db)):
    """List all clients."""
    clients = db.query(Client).all()
    return [{"id": str(c.id), "name": c.name} for c in clients]


# ══════════════════════════════════════════════
# BRAND ENDPOINTS
# ══════════════════════════════════════════════

@router.post("/brands")
def create_brand(req: CreateBrandRequest, db: Session = Depends(get_db)):
    """Add a new brand to track."""
    brand = Brand(
        client_id   = req.client_id,
        name        = req.name,
        domain      = req.domain,
        active_geos = req.geos,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return {
        "id":     str(brand.id),
        "name":   brand.name,
        "domain": brand.domain,
    }

@router.get("/brands")
def list_brands(db: Session = Depends(get_db)):
    """List all brands."""
    brands = db.query(Brand).all()
    return [
        {
            "id":     str(b.id),
            "name":   b.name,
            "domain": b.domain,
            "bio":    b.bio,
        }
        for b in brands
    ]

@router.get("/brands/{brand_id}")
def get_brand(brand_id: str, db: Session = Depends(get_db)):
    """Get a single brand by ID."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return {
        "id":             str(brand.id),
        "name":           brand.name,
        "domain":         brand.domain,
        "bio":            brand.bio,
        "bio_updated_at": brand.bio_updated_at,
        "active_geos":    brand.active_geos,
    }


class ScheduleRequest(BaseModel):
    auto_run_enabled: bool
    auto_run_day:      str  # "monday".."sunday"

@router.get("/brands/{brand_id}/schedule")
def get_schedule(brand_id: str, db: Session = Depends(get_db)):
    """Get current auto-run schedule settings for a brand."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return {
        "auto_run_enabled": brand.auto_run_enabled,
        "auto_run_day":     brand.auto_run_day,
        "last_auto_run":    brand.last_auto_run,
    }

@router.post("/brands/{brand_id}/schedule")
def set_schedule(brand_id: str, req: ScheduleRequest, db: Session = Depends(get_db)):
    """Enable/disable and configure automatic weekly pipeline runs."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
    if req.auto_run_day.lower() not in valid_days:
        raise HTTPException(status_code=400, detail=f"auto_run_day must be one of {valid_days}")

    brand.auto_run_enabled = req.auto_run_enabled
    brand.auto_run_day     = req.auto_run_day.lower()
    db.commit()

    return {
        "auto_run_enabled": brand.auto_run_enabled,
        "auto_run_day":     brand.auto_run_day,
    }


# ══════════════════════════════════════════════
# PIPELINE ENDPOINTS
# ══════════════════════════════════════════════

@router.post("/pipeline/run")
async def trigger_pipeline(req: RunPipelineRequest, db: Session = Depends(get_db)):
    """
    Trigger the full 7-stage pipeline for a brand.
    This runs: crawl → BIO → SERP → prompts → fire → parse → store
    """
    brand = db.query(Brand).filter(Brand.id == req.brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    print(f"\n🚀 Pipeline triggered for: {brand.domain}")
    result = await run_full_pipeline(req.brand_id, db)
    return result

@router.get("/pipeline/runs/{brand_id}")
def get_runs(brand_id: str, db: Session = Depends(get_db)):
    """Get all pipeline runs for a brand."""
    runs = db.query(Run).filter(Run.brand_id == brand_id).all()
    return [
        {
            "id":            str(r.id),
            "status":        r.status,
            "started_at":    r.started_at,
            "completed_at":  r.completed_at,
            "total_calls":   r.total_calls,
            "success_count": r.success_count,
            "failed_count":  r.failed_count,
        }
        for r in runs
    ]


# ══════════════════════════════════════════════
# DASHBOARD DATA ENDPOINTS
# ══════════════════════════════════════════════

@router.get("/dashboard/{brand_id}/overview")
def get_overview(brand_id: str, db: Session = Depends(get_db)):
    """
    Main dashboard overview for a brand.
    Returns: visibility score, mention rate, top competitors
    """
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    responses = db.query(Response).filter(Response.brand_id == brand_id).all()

    if not responses:
        return {"message": "No data yet — run the pipeline first"}

    total       = len(responses)
    mentioned   = sum(1 for r in responses if r.brand_mentioned)
    cited       = sum(1 for r in responses if r.brand_cited)

    visibility_score = round((mentioned / total) * 100, 1) if total > 0 else 0

    competitor_counts = {}
    for r in responses:
        for comp in (r.competing_brands or []):
            name = comp.get("brand_name", "")
            if name:
                competitor_counts[name] = competitor_counts.get(name, 0) + 1

    top_competitors = sorted(
        [{"brand": k, "mentions": v} for k, v in competitor_counts.items()],
        key=lambda x: x["mentions"],
        reverse=True
    )[:10]

    return {
        "brand_name":        brand.name,
        "total_responses":   total,
        "brand_mentioned":   mentioned,
        "brand_cited":       cited,
        "visibility_score":  visibility_score,
        "top_competitors":   top_competitors,
    }


@router.get("/dashboard/{brand_id}/by-geo")
def get_by_geo(brand_id: str, db: Session = Depends(get_db)):
    """Visibility breakdown by geography (IN, AE, GB)."""
    responses = db.query(Response).filter(Response.brand_id == brand_id).all()

    geo_data = {}
    for r in responses:
        geo = r.geo
        if geo not in geo_data:
            geo_data[geo] = {"total": 0, "mentioned": 0}
        geo_data[geo]["total"] += 1
        if r.brand_mentioned:
            geo_data[geo]["mentioned"] += 1

    return {
        geo: {
            "total":            data["total"],
            "mentioned":        data["mentioned"],
            "visibility_score": round(
                (data["mentioned"] / data["total"]) * 100, 1
            ) if data["total"] > 0 else 0,
        }
        for geo, data in geo_data.items()
    }


@router.get("/dashboard/{brand_id}/by-engine")
def get_by_engine(brand_id: str, db: Session = Depends(get_db)):
    """Visibility breakdown by AI engine (Gemini vs Perplexity)."""
    responses = db.query(Response).filter(Response.brand_id == brand_id).all()

    engine_data = {}
    for r in responses:
        engine = r.engine
        if engine not in engine_data:
            engine_data[engine] = {"total": 0, "mentioned": 0}
        engine_data[engine]["total"] += 1
        if r.brand_mentioned:
            engine_data[engine]["mentioned"] += 1

    return {
        engine: {
            "total":            data["total"],
            "mentioned":        data["mentioned"],
            "visibility_score": round(
                (data["mentioned"] / data["total"]) * 100, 1
            ) if data["total"] > 0 else 0,
        }
        for engine, data in engine_data.items()
    }


@router.get("/dashboard/{brand_id}/summary")
def get_executive_summary(brand_id: str, db: Session = Depends(get_db)):
    """
    AI-generated plain-English executive summary of the brand's
    visibility, built from the same data as the overview/geo/engine
    endpoints -- reads like something a brand manager could skim in
    10 seconds instead of scanning multiple charts.
    """
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    responses = db.query(Response).filter(Response.brand_id == brand_id).all()
    if not responses:
        return {"summary": "No data yet — run the pipeline first to generate a summary."}

    total = len(responses)
    mentioned = sum(1 for r in responses if r.brand_mentioned)
    visibility_score = round((mentioned / total) * 100, 1) if total > 0 else 0

    competitor_counts = {}
    for r in responses:
        for comp in (r.competing_brands or []):
            name = comp.get("brand_name", "")
            if name:
                competitor_counts[name] = competitor_counts.get(name, 0) + 1
    top_competitors = sorted(
        [{"brand": k, "mentions": v} for k, v in competitor_counts.items()],
        key=lambda x: x["mentions"], reverse=True
    )[:5]

    geo_data = {}
    for r in responses:
        geo_data.setdefault(r.geo, {"total": 0, "mentioned": 0})
        geo_data[r.geo]["total"] += 1
        if r.brand_mentioned:
            geo_data[r.geo]["mentioned"] += 1
    by_geo = {
        geo: round((d["mentioned"] / d["total"]) * 100, 1) if d["total"] > 0 else 0
        for geo, d in geo_data.items()
    }

    engine_data = {}
    for r in responses:
        engine_data.setdefault(r.engine, {"total": 0, "mentioned": 0})
        engine_data[r.engine]["total"] += 1
        if r.brand_mentioned:
            engine_data[r.engine]["mentioned"] += 1
    by_engine = {
        engine: round((d["mentioned"] / d["total"]) * 100, 1) if d["total"] > 0 else 0
        for engine, d in engine_data.items()
    }

    from app.services.claude_service import generate_executive_summary
    summary_text = generate_executive_summary(
        brand_name=brand.name,
        overview={
            "visibility_score": visibility_score,
            "total_responses": total,
            "top_competitors": [c["brand"] for c in top_competitors],
        },
        by_geo=by_geo,
        by_engine=by_engine,
    )

    return {"summary": summary_text}


@router.get("/dashboard/{brand_id}/by-intent")
def get_by_intent(brand_id: str, db: Session = Depends(get_db)):
    """Visibility breakdown by intent cluster."""
    responses = db.query(Response).filter(Response.brand_id == brand_id).all()

    intent_data = {}
    for r in responses:
        intent = r.intent_cluster
        if intent not in intent_data:
            intent_data[intent] = {"total": 0, "mentioned": 0}
        intent_data[intent]["total"] += 1
        if r.brand_mentioned:
            intent_data[intent]["mentioned"] += 1

    return {
        intent: {
            "total":            data["total"],
            "mentioned":        data["mentioned"],
            "visibility_score": round(
                (data["mentioned"] / data["total"]) * 100, 1
            ) if data["total"] > 0 else 0,
        }
        for intent, data in intent_data.items()
    }


class FireSelectedPromptsRequest(BaseModel):
    brand_id:   str
    prompt_ids: list[str]


@router.get("/brands/{brand_id}/prompts")
def get_prompts(brand_id: str, db: Session = Depends(get_db)):
    """
    Get all generated prompts for a brand.
    Frontend shows these so user can select 5-10 to fire.
    """
    prompts = db.query(Prompt).filter(
        Prompt.brand_id == brand_id,
        Prompt.status   == "active"
    ).all()

    return [
        {
            "id":             str(p.id),
            "prompt_text":    p.prompt_text,
            "intent_cluster": p.intent_cluster,
            "prompt_type":    p.prompt_type,
        }
        for p in prompts
    ]


@router.post("/pipeline/fire-selected")
async def fire_selected_prompts(
    req: FireSelectedPromptsRequest,
    db: Session = Depends(get_db)
):
    """
    Fire user-selected prompts at both Gemini and OpenAI,
    across all 3 geos (IN/AE/GB).
    User picks 1-10 from the generated list.
    """
    brand = db.query(Brand).filter(Brand.id == req.brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if len(req.prompt_ids) < 1 or len(req.prompt_ids) > 10:
        raise HTTPException(
            status_code=400,
            detail="Please select between 1 and 10 prompts"
        )

    prompts = db.query(Prompt).filter(
        Prompt.id.in_(req.prompt_ids)
    ).all()

    from datetime import datetime
    run = Run(
        brand_id     = req.brand_id,
        triggered_by = "manual_selected",
        status       = "running",
        started_at   = datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    bio           = brand.bio or {}
    brand_name    = bio.get("brand_name", brand.domain)
    brand_aliases = bio.get("aliases", [])
    results       = []

    from app.services.pipeline import fire_gemini, fire_openai
    from app.services.claude_service import parse_response, find_brand_source_urls

    ENGINES = ["gemini", "openai"]
    GEOS    = ["IN", "AE", "GB"]

    for prompt in prompts:
        for geo in GEOS:
            for engine in ENGINES:
                print(f"\n🔥 Firing [{engine}/{geo}]: {prompt.prompt_text[:60]}...")

                if engine == "gemini":
                    fired = await fire_gemini(prompt.prompt_text, geo)
                else:
                    fired = await fire_openai(prompt.prompt_text, geo)

                raw = fired.get("raw_text", "")
                if not raw:
                    continue

                citation_urls = [
                    s.get("uri") or s.get("url", "")
                    for s in fired.get("source_urls", [])
                ]

                # Parse the response
                parsed = parse_response(raw, brand_name, brand_aliases)

                brand_source_urls = find_brand_source_urls(
                    fired.get("source_urls", []),
                    brand.domain,
                    brand_name,
                    brand_aliases=brand_aliases,
                    grounding_supports=fired.get("grounding_supports", []),
                    brand_was_mentioned=parsed.get("brand_mentioned", False),
                )

                # Save to DB
                response_record = Response(
                    run_id            = run.id,
                    brand_id          = req.brand_id,
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

                results.append({
                    "prompt_text":       prompt.prompt_text,
                    "engine":            engine,
                    "geo":               geo,
                    "intent_cluster":    prompt.intent_cluster,
                    "brand_mentioned":   parsed.get("brand_mentioned", False),
                    "brand_cited":       parsed.get("brand_cited", False),
                    "mention_form":      parsed.get("mention_form", "none"),
                    "brand_source_urls": brand_source_urls,
                    "raw_response":      raw[:500],
                })

    db.commit()

    run.status        = "complete"
    run.completed_at  = datetime.utcnow()
    run.total_calls   = len(results)
    run.success_count = len(results)
    db.commit()

    return {
        "run_id":  str(run.id),
        "total":   len(results),
        "results": results,
    }


# ══════════════════════════════════════════════
# STAGED PIPELINE ENDPOINTS
# ══════════════════════════════════════════════

class CrawlRequest(BaseModel):
    brand_id: str

class ApprovePromptRequest(BaseModel):
    brand_id: str

@router.post("/pipeline/crawl-and-bio")
async def crawl_and_extract_bio(
    req: CrawlRequest,
    db: Session = Depends(get_db)
):
    """
    Stage A — Crawl the brand website and extract BIO.
    Returns the BIO for user review before generating prompts.
    """
    brand = db.query(Brand).filter(Brand.id == req.brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    # Pull out the plain values we need, then release this connection
    # back to the pool BEFORE the long-running crawl starts.
    #
    # Why: the crawl below can take 30-90+ seconds (10+ sequential page
    # loads, several via a headless browser with multi-second scroll/
    # wait delays). If we kept this DB session open the whole time, the
    # connection sits idle for that entire window -- and cloud Postgres
    # (Render, etc.) commonly closes idle SSL connections in the
    # background. SQLAlchemy's pool_pre_ping only re-validates a
    # connection at the moment it's freshly checked out from the pool --
    # since this one was checked out once at the start of the request
    # and never returned, pre_ping never got a chance to catch that it
    # had gone stale, and the final db.commit() failed with
    # "SSL connection has been closed unexpectedly".
    #
    # Closing here returns the connection to the pool immediately, and
    # opening a NEW session below (right before the write) forces a
    # fresh checkout -- which pool_pre_ping WILL validate, transparently
    # reconnecting if needed.
    brand_id     = str(brand.id)
    brand_domain = brand.domain
    brand_name   = brand.name
    db.close()

    from app.services.serp_service import crawl_brand
    from app.services.claude_service import extract_bio
    from app.models.database import SessionLocal
    from datetime import datetime

    print(f"\n🔍 Stage A: Crawling {brand_domain}...")

    corpus = crawl_brand(brand_domain)
    if not corpus:
        raise HTTPException(status_code=500, detail="Crawl failed — not enough pages found")

    bio = extract_bio(corpus, brand_domain)
    if not bio:
        raise HTTPException(status_code=500, detail="BIO extraction failed")

    # Fresh session for the write -- see note above for why this can't
    # just reuse the `db` session injected at the top of the request.
    write_db = SessionLocal()
    try:
        brand_row = write_db.query(Brand).filter(Brand.id == req.brand_id).first()
        if not brand_row:
            raise HTTPException(status_code=404, detail="Brand not found")

        brand_row.bio            = bio
        brand_row.bio_updated_at = datetime.utcnow()
        write_db.commit()
    finally:
        write_db.close()

    print(f"✅ BIO extracted and saved for {brand_domain}")
    return {
        "brand_id":   brand_id,
        "brand_name": brand_name,
        "bio":        bio,
    }


@router.post("/pipeline/generate-prompts")
async def generate_prompts(
    req: ApprovePromptRequest,
    db: Session = Depends(get_db)
):
    """
    Stage B — User approved the BIO.
    Now run Stage 4+5: SERP enrichment + prompt construction.
    Returns the generated prompts for user to review and select from.
    """
    brand = db.query(Brand).filter(Brand.id == req.brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if not brand.bio:
        raise HTTPException(
            status_code=400,
            detail="No BIO found — run crawl and BIO extraction first"
        )

    from app.services.serp_service import enrich_from_serp
    from app.services.claude_service import construct_prompts

    print(f"\n📝 Stage B: Generating prompts for {brand.domain}...")

    raw_signals = enrich_from_serp(brand.bio)
    if not raw_signals:
        raise HTTPException(status_code=500, detail="SERP enrichment failed")

    prompt_dicts = construct_prompts(brand.bio, raw_signals)
    if not prompt_dicts:
        raise HTTPException(status_code=500, detail="Prompt construction failed")
    old_prompt_ids = [p.id for p in db.query(Prompt).filter(Prompt.brand_id == brand.id).all()]

    if old_prompt_ids:
        db.query(Response).filter(Response.prompt_id.in_(old_prompt_ids)).delete(
        synchronize_session=False)
        db.commit()
        db.query(Prompt).filter(Prompt.brand_id == brand.id).delete(
        synchronize_session=False)
        db.commit()

    saved = []
    for p in prompt_dicts[:50]:
        prompt = Prompt(
            brand_id       = brand.id,
            prompt_text    = p.get("prompt_text", ""),
            intent_cluster = p.get("intent_cluster", "informational"),
            prompt_type    = p.get("prompt_type", "category"),
            source_signals = [p.get("source_signal", "")],
        )
        db.add(prompt)
        saved.append(prompt)

    db.commit()
    print(f"✅ {len(saved)} prompts saved")

    db.refresh(saved[0])
    return {
        "total_prompts": len(saved),
        "prompts": [
            {
                "id":             str(p.id),
                "prompt_text":    p.prompt_text,
                "intent_cluster": p.intent_cluster,
                "prompt_type":    p.prompt_type,
            }
            for p in saved
        ]
    }


# ══════════════════════════════════════════════
# TIME SERIES — TREND DATA
# ══════════════════════════════════════════════

import sqlalchemy
from sqlalchemy import func, extract

@router.get("/dashboard/{brand_id}/trend")
def get_trend(brand_id: str, db: Session = Depends(get_db)):
    """
    Returns month-by-month visibility trend data.
    Shows how the brand's AI visibility score changes over time.
    """
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    results = (
        db.query(
            extract("year",  Response.run_date).label("year"),
            extract("month", Response.run_date).label("month"),
            func.count(Response.id).label("total"),
            func.sum(
                func.cast(Response.brand_mentioned, sqlalchemy.Integer)
            ).label("mentioned"),
        )
        .filter(Response.brand_id == brand_id)
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    if not results:
        return []

    trend = []
    for row in results:
        total    = row.total or 0
        mentioned = int(row.mentioned or 0)
        score    = round((mentioned / total) * 100, 1) if total > 0 else 0

        import calendar
        month_name = calendar.month_abbr[int(row.month)]
        label      = f"{month_name} {int(row.year)}"

        trend.append({
            "month":            label,
            "visibility_score": score,
            "total_responses":  total,
            "brand_mentioned":  mentioned,
        })

    return trend