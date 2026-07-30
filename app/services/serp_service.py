import requests
from bs4 import BeautifulSoup
from app.config import settings

# ══════════════════════════════════════════════
# STAGE 1 — BRAND PAGE DISCOVERY
# ══════════════════════════════════════════════

def discover_brand_pages(domain: str) -> list[dict]:
    """
    Uses SerpAPI Google Search with site:domain query
    to find the top 100 pages ranked by Google authority.
    Returns list of dicts with url, title, snippet, position.
    """
    try:
        params = {
            "engine":   "google",
            "q":        f"site:{domain}",
            "num":      100,
            "api_key":  settings.SERP_API_KEY,
        }
        response = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=30
        )
        data = response.json()

        # SerpAPI returns an "error" field (no organic_results at all) when
        # something's wrong -- quota exhausted, invalid key, malformed query,
        # etc. Without this check, that silently looks like "0 pages found"
        # with no indication of why, which wastes time debugging the wrong
        # thing (crawler/domain) instead of the real cause (the API call).
        if "error" in data:
            print(f"❌ SerpAPI returned an error for '{domain}': {data['error']}")
            return []

        pages = []
        for result in data.get("organic_results", []):
            url   = result.get("link", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            position = result.get("position", 0)

            is_priority = any(
                keyword in url.lower()
                for keyword in [
                    "/product", "/collection", "/category",
                    "/shop", "/faq", "/review"
                ]
            )

            pages.append({
                "url":         url,
                "title":       title,
                "snippet":     snippet,
                "position":    position,
                "is_priority": is_priority,
            })

        pages.sort(key=lambda x: (not x["is_priority"], x["position"]))

        print(f"✅ Found {len(pages)} pages for {domain}")
        return pages

    except Exception as e:
        print(f"❌ Error discovering pages for {domain}: {e}")
        return []


# ══════════════════════════════════════════════
# STAGE 2 — PAGE CRAWL AND CONTENT EXTRACTION
# ──────────────────────────────────────────────
# Now tries a fast requests-based crawl first, and falls back to a
# real headless browser (Playwright) if the page comes back looking
# empty -- which is what happens on JS-rendered storefronts
# (React/Next.js sites like The Souled Store) where the real content
# never appears in the plain HTML response.
# ══════════════════════════════════════════════

def crawl_page(url: str) -> dict:
    """
    Fetches a single page and extracts clean text.
    Strips: navigation, footer, scripts, cookie banners.
    Keeps: headings, product descriptions, FAQs, reviews.

    Strategy:
      1. Try a fast requests + BeautifulSoup crawl.
      2. If that returns too little text (likely a JS-rendered page),
         fall back to Playwright, which runs a real headless browser
         so JavaScript actually executes before we read the content.
    """
    result = _crawl_with_requests(url)
    if result["success"]:
        return result

    print(f"  🔄 Falling back to Playwright for: {url}")
    return _crawl_with_playwright(url)


def _crawl_with_requests(url: str) -> dict:
    """Fast crawl using requests + BeautifulSoup (original Stage 2 logic)."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
        response = requests.get(url, headers=headers, timeout=10)

        # Some storefronts (Shopify, etc.) rate-limit or bot-block rapid
        # sequential requests with a 503. Retry once after a short pause
        # before giving up on this page.
        if response.status_code == 503:
            import time
            time.sleep(3)
            response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            print(f"⚠️  Skipping {url} — status {response.status_code}")
            return {"url": url, "text": "", "success": False}

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["nav", "footer", "script", "style", "header",
                         "aside", "iframe", "noscript", "form"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)

        import re
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) < 100:
            # This used to fail SILENTLY -- no print statement -- which is
            # exactly why "0/30 crawled" was hard to diagnose for sites
            # like this one. Now it tells you WHY: either the page really
            # has almost no content, or (more likely for JS-heavy modern
            # storefronts) the real content is rendered by JavaScript and
            # our plain-HTML fetch only sees an empty page shell.
            #
            # Rather than giving up here, we return success=False so the
            # caller (crawl_page) can retry this URL with Playwright.
            print(f"⚠️  {url} — only {len(text)} chars via requests "
                  f"(page may be JS-rendered) — will retry with Playwright")
            return {"url": url, "text": "", "success": False}

        print(f"✅ Crawled {url} — {len(text)} characters (requests)")
        return {
            "url":     url,
            "text":    text[:5000],
            "success": True,
        }

    except Exception as e:
        print(f"❌ Error crawling {url} with requests: {e}")
        return {"url": url, "text": "", "success": False}


def _crawl_with_playwright(url: str) -> dict:
    """
    Slower but powerful crawl using Playwright.
    Actually runs a real headless browser so JavaScript executes,
    then reads the fully-rendered HTML. Used as a fallback for
    React/Next.js storefronts (e.g. The Souled Store) where a plain
    requests.get() only sees an empty page shell.

    Requires:
        pip install playwright
        playwright install chromium

    IMPORTANT: Playwright's Sync API refuses to run in any thread that
    already has an asyncio event loop running -- and FastAPI's request
    handler thread always does. Calling sync_playwright() directly here
    raises "Sync API inside the asyncio loop". The fix is to run the
    actual browser work in a dedicated worker thread (via
    ThreadPoolExecutor) that has no event loop of its own, and block
    here until it finishes. This avoids rewriting the whole crawler
    (crawl_page / crawl_brand) as async just for this one fallback.
    """
    from concurrent.futures import ThreadPoolExecutor
    import re

    def _run_sync_playwright() -> str:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # A couple of launch args that avoid the most basic signals
            # sites use to fingerprint headless Chrome specifically
            # (as opposed to a real browser).
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # NOTE: "networkidle" was dropped -- sites like this keep
            # background analytics/tracking requests pinging forever,
            # so the page never truly goes idle and the wait just times
            # out (that's what caused the earlier empty-message errors).
            # domcontentloaded + a fixed settle time is more reliable.
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # Many e-commerce category pages lazy-load the actual
            # product grid only once it scrolls into view. Scroll down
            # in a couple of steps and pause between each to give that
            # lazy content a chance to fetch and render.
            for _ in range(3):
                page.evaluate("window.scrollBy(0, document.body.scrollHeight / 3)")
                page.wait_for_timeout(1200)

            html = page.content()
            browser.close()
            return html

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            # Raised from 30s -> 45s: scrolling + settle waits above take
            # longer than the original fixed 2s did, so the old timeout
            # was cutting things off mid-load on some pages.
            html = executor.submit(_run_sync_playwright).result(timeout=45)

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["nav", "footer", "script", "style", "header",
                         "aside", "iframe", "noscript", "form"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) < 100:
            # DEBUG: print what was actually captured so we can tell
            # apart "genuinely empty/still loading" from "this is a bot
            # -detection / CAPTCHA / block page" -- the fix is completely
            # different depending on which one it is.
            print(f"⚠️  Skipping {url} — only {len(text)} chars even via "
                  f"Playwright (page may be genuinely empty or blocking bots)")
            print(f"    DEBUG raw text captured: {text!r}")
            return {"url": url, "text": "", "success": False}

        print(f"✅ Crawled {url} — {len(text)} characters (Playwright)")
        return {
            "url":     url,
            "text":    text[:5000],
            "success": True,
        }

    except Exception as e:
        # concurrent.futures.TimeoutError (and a few others) stringify to
        # an empty message, which is why earlier logs showed
        # "Playwright error for <url>: " with nothing after the colon.
        # Including the exception type makes those readable too.
        print(f"❌ Playwright error for {url}: [{type(e).__name__}] {e}")
        return {"url": url, "text": "", "success": False}


# ══════════════════════════════════════════════
# COMBINED — CRAWL TOP PAGES FOR A BRAND
# ══════════════════════════════════════════════

def crawl_brand(domain: str) -> list[dict]:
    """
    Full crawl pipeline for one brand:
    1. Discover top pages via SerpAPI
    2. Crawl top 30 pages
    3. Return clean text corpus
    """
    print(f"\n🔍 Starting crawl for: {domain}")

    pages = discover_brand_pages(domain)

    if len(pages) < 5:
        print(f"❌ Too few pages found for {domain} — cannot continue")
        return []

    top_pages  = pages[:30]
    corpus     = []
    successful = 0

    import time
    for i, page in enumerate(top_pages):
        result = crawl_page(page["url"])
        if result["success"]:
            corpus.append({
                "url":   result["url"],
                "title": page["title"],
                "text":  result["text"],
            })
            successful += 1
        # Small delay between requests -- avoids tripping rate-limit /
        # bot-detection on storefronts (Shopify etc.) that block rapid
        # sequential requests.
        if i < len(top_pages) - 1:
            time.sleep(1.5)

    print(f"\n✅ Crawl complete: {successful}/30 pages successfully crawled")

    if successful < 5:
        print(f"❌ Only {successful} pages crawled — too few to continue")
        return []

    return corpus


# ══════════════════════════════════════════════
# STAGE 4A — GOOGLE RELATED QUESTIONS (PAA)
# ──────────────────────────────────────────────
# Now also seeds from target_personas -- surfaces real "who uses this"
# category questions, not just attribute-driven ones (per JD's feedback).
# ══════════════════════════════════════════════

def get_paa_questions(bio: dict) -> list[str]:
    """
    Uses BIO fields (category_keywords, product_attributes, use_cases,
    AND target_personas) as seed terms to query Google PAA via SerpAPI.
    Returns list of real questions shoppers ask.
    """

    seed_terms = []
    seed_terms.extend(bio.get("category_keywords", [])[:6])
    seed_terms.extend(bio.get("product_attributes", [])[:5])
    seed_terms.extend(bio.get("use_cases", [])[:5])

    categories = bio.get("product_categories", [])[:2]
    personas   = bio.get("target_personas", [])[:4]
    for persona in personas:
        for cat in categories:
            seed_terms.append(f"best {cat} for {persona}")
            seed_terms.append(f"what {cat} do {persona} use")

    seed_terms = seed_terms[:20]

    all_questions = []

    for term in seed_terms:
        try:
            params = {
                "engine":  "google",
                "q":       term,
                "api_key": settings.SERP_API_KEY,
                "gl":      "in",
                "hl":      "en",
            }
            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=15
            )
            data = response.json()

            for item in data.get("related_questions", []):
                question = item.get("question", "")
                if question and question not in all_questions:
                    all_questions.append(question)

            print(f"  ✅ PAA: '{term}' → {len(data.get('related_questions', []))} questions")

        except Exception as e:
            print(f"  ❌ PAA error for '{term}': {e}")
            continue

    print(f"\n✅ Total PAA questions collected: {len(all_questions)}")
    return all_questions


# ══════════════════════════════════════════════
# STAGE 4B — GOOGLE AUTOCOMPLETE
# ──────────────────────────────────────────────
# Now also seeds from target_personas.
# ══════════════════════════════════════════════

def get_autocomplete_signals(bio: dict) -> list[str]:
    """
    Uses BIO-derived seed fragments (including personas) to query
    Google Autocomplete via SerpAPI.
    Returns list of autocomplete completions.
    """

    categories   = bio.get("product_categories", [])[:3]
    attributes   = bio.get("product_attributes", [])[:3]
    use_cases    = bio.get("use_cases", [])[:3]
    competitors  = bio.get("competitor_signals", [])[:2]
    personas     = bio.get("target_personas", [])[:3]

    seed_fragments = []

    for cat in categories:
        for use in use_cases:
            seed_fragments.append(f"best {cat} for {use}")

        for attr in attributes:
            seed_fragments.append(f"{cat} for {attr}")

        for comp in competitors:
            seed_fragments.append(f"{cat} vs {comp}")

        for persona in personas:
            seed_fragments.append(f"which {cat} brand is good for {persona}")
            seed_fragments.append(f"best {cat} {persona} recommend")
            seed_fragments.append(f"what do {persona} look for in {cat}")

    seed_fragments = seed_fragments[:35]

    all_completions = []

    for fragment in seed_fragments:
        try:
            params = {
                "engine":  "google_autocomplete",
                "q":       fragment,
                "api_key": settings.SERP_API_KEY,
                "gl":      "in",
                "hl":      "en",
            }
            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=15
            )
            data = response.json()

            for suggestion in data.get("suggestions", []):
                value = suggestion.get("value", "")
                if value and value not in all_completions:
                    all_completions.append(value)

            print(f"  ✅ Autocomplete: '{fragment[:40]}' → {len(data.get('suggestions', []))} suggestions")

        except Exception as e:
            print(f"  ❌ Autocomplete error for '{fragment[:40]}': {e}")
            continue

    print(f"\n✅ Total autocomplete signals: {len(all_completions)}")
    return all_completions


# ══════════════════════════════════════════════
# COMBINED — FULL SERP ENRICHMENT
# ══════════════════════════════════════════════

def enrich_from_serp(bio: dict) -> list[str]:
    """
    Full Stage 4 pipeline:
    1. Get PAA questions
    2. Get Autocomplete signals
    3. Combine and deduplicate
    Returns unique signals
    """
    print(f"\n🔎 Starting SERP enrichment for: {bio.get('brand_name', 'unknown')}")

    paa_questions       = get_paa_questions(bio)
    autocomplete_signals = get_autocomplete_signals(bio)

    all_signals = paa_questions + autocomplete_signals

    seen     = set()
    unique   = []
    for signal in all_signals:
        normalized = signal.lower().strip()
        if normalized not in seen and len(signal) > 10:
            seen.add(normalized)
            unique.append(signal)

    print(f"\n✅ SERP enrichment complete:")
    print(f"   PAA questions:        {len(paa_questions)}")
    print(f"   Autocomplete signals: {len(autocomplete_signals)}")
    print(f"   After deduplication:  {len(unique)} unique signals")

    return unique
