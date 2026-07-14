import json
import re
from datetime import datetime
from difflib import SequenceMatcher
from google import genai
from app.config import settings

# Initialize new Gemini client
client = genai.Client(api_key=settings.GEMINI_API_KEY)


def call_gemini(prompt: str, system: str = "") -> str:
    """Generic Gemini call using the new google.genai SDK."""
    try:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=full_prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return ""

# ══════════════════════════════════════════════
# STAGE 3 — BIO EXTRACTION (hallucination-verified)
# ──────────────────────────────────────────────
# Every product_attribute / competitor_signal / review_signal Gemini
# extracts must come with a verbatim source_quote. We then check that
# quote actually appears in the crawled text (fuzzy match). Anything
# that fails verification is dropped, not silently kept -- this is what
# catches invented details like "3-layer SpaceWalk soles" before they
# ever reach the prompt-generation stage.
# ══════════════════════════════════════════════

def _quote_appears_in_source(quote: str, source_text: str, min_quote_words: int = 4) -> bool:
    """
    Strict verification -- the quote must appear ALMOST VERBATIM in the
    source text, not just share a few common words.

    Previous version accepted a match if ANY 3 consecutive words from the
    quote appeared in the source. That was too lenient: a fabricated quote
    like "the sole uses a 3-layer space design for comfort" could pass by
    sharing only "for comfort" with unrelated real text. This version
    requires either an exact substring match, or a long, high-similarity
    match using a sliding window comparison -- much harder for an invented
    quote to satisfy by accident.
    """
    if not quote or len(quote.strip()) < 3:
        return False

    def normalize(s):
        s = s.lower()
        s = re.sub(r'[^\w\s]', '', s)   # strip punctuation
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    norm_quote  = normalize(quote)
    norm_source = normalize(source_text)

    quote_words = norm_quote.split()
    if len(quote_words) < min_quote_words:
        # Too short to verify reliably -- reject rather than risk a
        # coincidental match on a generic short phrase.
        return False

    # 1. Exact substring match (strongest signal)
    if norm_quote in norm_source:
        return True

    # 2. Near-exact match via sliding window: the FULL quote (not a
    #    fragment) must have high similarity to some equal-length window
    #    of the source text. This catches minor whitespace/OCR-style
    #    differences but rejects quotes that are mostly fabricated.
    source_words = norm_source.split()
    window_size = len(quote_words)

    for i in range(0, max(1, len(source_words) - window_size + 1)):
        window = " ".join(source_words[i:i + window_size])
        similarity = SequenceMatcher(None, norm_quote, window).ratio()
        if similarity >= 0.85:  # high bar -- near-verbatim, not just related
            return True

    return False


def _extract_suspicious_terms(text: str) -> list[str]:
    """
    Extract camelCase-style compound words (e.g. 'SpaceWalk', 'AirFlex') --
    a classic pattern for fabricated proprietary tech/material names. Real
    brand tech names are rare enough that any such term found in an
    attribute MUST be verified directly against the source, independent
    of whether the accompanying quote happens to be real.
    """
    return re.findall(r'\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b', text)


def _attribute_is_grounded(attribute: str, quote: str, source_text: str) -> bool:
    """
    Two-layer check:
    1. The quote must genuinely appear in the source (existing check).
    2. Any suspicious proper-noun/trademark-style term in the ATTRIBUTE
       itself must ALSO appear verbatim in the source text -- this closes
       the loophole where a real (but unrelated) quote is paired with a
       fabricated specific term like "SpaceWalk". Without this, a model
       can satisfy quote verification with genuine text while still
       inventing the specific claim itself.
    """
    if not _quote_appears_in_source(quote, source_text):
        return False

    suspicious_terms = _extract_suspicious_terms(attribute)
    if suspicious_terms:
        source_lower = source_text.lower()
        for term in suspicious_terms:
            if term.lower() not in source_lower:
                return False  # invented proper noun, reject regardless of quote

    return True


def extract_bio(corpus: list[dict], domain: str) -> dict:
    """Extract Brand Intelligence Object using Gemini, with hallucination
    verification on every extracted attribute/signal."""

    combined_text = "\n\n".join([
        f"PAGE: {page['title']}\nURL: {page['url']}\n{page['text']}"
        for page in corpus
    ])
    combined_text = combined_text[:50000]

    print(f"📄 Sending {len(combined_text)} characters to Gemini for BIO extraction...")

    system = """You are a brand intelligence analyst. You extract ONLY
information that is explicitly present in the provided text. You NEVER
invent, infer, or embellish product features, technology names, or
specifications that are not directly stated in the source content.
If you are not certain something is explicitly stated, do not include it.
Return ONLY valid JSON matching the schema provided."""

    prompt = f"""Extract brand intelligence from this website content.

DOMAIN: {domain}

CRITICAL ANTI-HALLUCINATION RULE:
For EVERY item in product_attributes, review_signals, and
competitor_signals, you MUST include the exact verbatim sentence or
phrase from the source text that supports it. If you cannot find a
direct quote supporting an attribute, DO NOT include that attribute at
all. Do not invent technology names, material names, or specifications
that are not literally written in the page content. Generic attributes
("lightweight", "breathable") are fine ONLY if those words or close
synonyms actually appear in the source text.

SCHEMA TO EXTRACT:
{{
    "brand_name": "Official name and known aliases",
    "domain": "root domain",
    "product_categories": ["list of top-level categories"],
    "product_attributes": [
        {{"attribute": "functional attribute text", "source_quote": "exact verbatim quote from page content that supports this", "generic_equivalent": "the SAME attribute described in plain, brand-neutral functional language a shopper would use, with NO proprietary/trademarked technology names -- e.g. if attribute is 'SpaceWalk 3-layer sole', generic_equivalent should be 'multi-layer cushioned sole'"}}
    ],
    "use_cases": ["occasions and usage contexts"],
    "target_personas": [
        {{"persona": "who typically buys/uses this category", "source_quote": "exact verbatim quote from page content, imagery caption, or product framing that supports this persona"}}
    ],
    "price_positioning": "premium or mid-market or value",
    "competitor_signals": [
        {{"brand_name": "CompetitorName", "source_quote": "exact verbatim quote mentioning this competitor"}}
    ],
    "geo_markets": ["markets indicated by currency, language, shipping"],
    "category_keywords": ["category-level keywords — must NOT include brand name"],
    "review_signals": [
        {{"signal": "attribute phrase from reviews", "source_quote": "exact verbatim quote from a review/testimonial"}}
    ],
    "confidence_flags": ["field names where extraction confidence is low"]
}}

RULES:
- product_attributes must include functional/physical attributes a shopper would use
- category_keywords must NOT contain the brand name
- price_positioning: infer from visible pricing or product description language
- confidence_flags: list field names where you could not find enough evidence
- target_personas: base this on actual product framing/imagery/copy in the
  text (e.g. "for athletes", "office wear", "kids") -- not generic guesses

PAGE CONTENT:
{combined_text}"""

    try:
        raw_text = call_gemini(prompt, system)
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        raw_bio = json.loads(raw_text)

        dropped = []

        verified_attributes = []
        for item in raw_bio.get("product_attributes", []):
            if isinstance(item, str):
                dropped.append({"type": "product_attribute", "value": item, "reason": "no_source_quote_provided"})
                continue
            attr = item.get("attribute", "")
            quote = item.get("source_quote", "")
            if _attribute_is_grounded(attr, quote, combined_text):
                verified_attributes.append(attr)
            else:
                dropped.append({"type": "product_attribute", "value": attr, "quote": quote, "reason": "quote_not_found_or_invented_term"})

        verified_competitors = []
        for item in raw_bio.get("competitor_signals", []):
            if isinstance(item, str):
                dropped.append({"type": "competitor_signal", "value": item, "reason": "no_source_quote_provided"})
                continue
            name = item.get("brand_name", "")
            quote = item.get("source_quote", "")
            if _quote_appears_in_source(quote, combined_text):
                verified_competitors.append(name)
            else:
                dropped.append({"type": "competitor_signal", "value": name, "quote": quote, "reason": "quote_not_found_in_source"})

        verified_reviews = []
        for item in raw_bio.get("review_signals", []):
            if isinstance(item, str):
                dropped.append({"type": "review_signal", "value": item, "reason": "no_source_quote_provided"})
                continue
            signal = item.get("signal", "")
            quote = item.get("source_quote", "")
            if _quote_appears_in_source(quote, combined_text):
                verified_reviews.append(signal)
            else:
                dropped.append({"type": "review_signal", "value": signal, "quote": quote, "reason": "quote_not_found_in_source"})

        verified_personas = []
        for item in raw_bio.get("target_personas", []):
            if isinstance(item, str):
                dropped.append({"type": "target_persona", "value": item, "reason": "no_source_quote_provided"})
                continue
            persona = item.get("persona", "")
            quote = item.get("source_quote", "")
            if _quote_appears_in_source(quote, combined_text):
                verified_personas.append(persona)
            else:
                dropped.append({"type": "target_persona", "value": persona, "quote": quote, "reason": "quote_not_found_in_source"})

        bio = {
            "brand_name":          raw_bio.get("brand_name", ""),
            "domain":              domain,
            "product_categories":  raw_bio.get("product_categories", []),
            "product_attributes":  verified_attributes,
            "use_cases":           raw_bio.get("use_cases", []),
            "target_personas":     verified_personas,
            "price_positioning":   raw_bio.get("price_positioning", ""),
            "competitor_signals":  verified_competitors,
            "geo_markets":         raw_bio.get("geo_markets", []),
            "category_keywords":   raw_bio.get("category_keywords", []),
            "review_signals":      verified_reviews,
            "confidence_flags":    raw_bio.get("confidence_flags", []),
            "bio_version":         "2.0",
            "crawl_date":          datetime.utcnow().isoformat(),
            "_dropped_hallucinations": dropped,
        }

        print(f"✅ BIO extracted for {domain}")
        print(f"   Brand: {bio.get('brand_name', 'unknown')}")
        print(f"   Verified attributes: {len(verified_attributes)}")
        if dropped:
            print(f"   ⚠️  Dropped {len(dropped)} unverifiable items (see bio['_dropped_hallucinations']):")
            for d in dropped:
                print(f"      - [{d['type']}] '{d['value']}' -- {d['reason']}")

        return bio

    except json.JSONDecodeError as e:
        print(f"❌ Gemini returned invalid JSON: {e}")
        return {}
    except Exception as e:
        print(f"❌ Error extracting BIO: {e}")
        return {}


# ══════════════════════════════════════════════
# GENERICIZE ATTRIBUTES
# ──────────────────────────────────────────────
# A verified attribute can still be a problem for prompt generation even
# if it's 100% real: coined/proprietary tech names ("SpaceWalk soles",
# "AirFlex cushioning") are unique enough that a question built around
# them will ALWAYS surface the brand -- which defeats the purpose of a
# visibility test. This step rewrites each verified attribute into the
# generic, category-standard language a real shopper would use to
# describe the underlying benefit, with no coined names attached.
# Example: "3-layer SpaceWalk soles" -> "multi-layer cushioned soles"
# ══════════════════════════════════════════════

def genericize_attributes(verified_attributes: list[str], product_categories: list[str]) -> list[str]:
    """
    Rewrites brand-specific/coined attribute names into generic,
    category-standard descriptions a shopper would use without knowing
    the brand's marketing term for it. Falls back to the original
    attribute if genericization fails.
    """
    if not verified_attributes:
        return []

    numbered = "\n".join(f"{i+1}. {a}" for i, a in enumerate(verified_attributes))

    prompt = f"""These are verified product attributes for a brand in this category: {product_categories}

ATTRIBUTES:
{numbered}

For EACH attribute, rewrite it as a GENERIC, category-standard description
of the underlying functional benefit -- the way any shopper would describe
it WITHOUT knowing this brand's specific marketing name for it.

RULES:
- Strip out any coined/proprietary/trademark-sounding technology names
  (e.g. "SpaceWalk soles" -> "cushioned multi-layer soles",
  "AirFlex cushioning" -> "flexible air cushioning").
- Keep the real functional meaning intact -- don't lose the actual benefit,
  just remove brand-unique naming.
- If an attribute is already generic (e.g. "lightweight", "breathable"),
  return it unchanged.
- Each generic version should be phrasing multiple competing brands could
  plausibly also use to describe similar features.

Return ONLY a JSON array of strings, same order and length as input, no other text:
["generic version 1", "generic version 2", ...]"""

    try:
        raw_text = call_gemini(
            prompt,
            "You are a product copywriter who removes brand-specific jargon. Return ONLY a valid JSON array of strings."
        )
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        generic = json.loads(raw_text)
        if len(generic) != len(verified_attributes):
            print("⚠️  Genericize count mismatch -- falling back to originals")
            return verified_attributes
        print(f"✅ Genericized {len(generic)} attributes")
        return generic
    except Exception as e:
        print(f"❌ Error genericizing attributes: {e} -- falling back to originals")
        return verified_attributes


# ══════════════════════════════════════════════
# STAGE 5 — PROMPT CONSTRUCTION + REVIEW AGENT
# ──────────────────────────────────────────────
# Pipeline: generate MORE than needed (BIO-grounded, brand-name-free)
#   -> rule filter (deterministic: kills brand mentions, dupes, generic)
#   -> Gemini scores survivors (specificity, naturalness, usefulness)
#   -> return top N, ranked, with scores attached
# ══════════════════════════════════════════════

def generate_candidate_prompts(bio: dict, raw_signals: list[str], target_count: int = 80) -> list[dict]:
    """
    Generate MORE candidates than we need, forced to combine specific BIO
    fields (attribute + use_case + persona + price_positioning) so each
    prompt tests something only THIS brand's actual traits would answer --
    not a generic "X vs Y" any brand could substitute into.
    """
    brand_name   = bio.get("brand_name", "")
    attributes   = bio.get("product_attributes", [])
    use_cases    = bio.get("use_cases", [])
    personas     = bio.get("target_personas", [])
    categories   = bio.get("product_categories", [])
    price        = bio.get("price_positioning", "")

    signals_to_use = raw_signals[:60]

    prompt = f"""Generate shopper questions that test a brand's AI visibility.

CORE PRINCIPLE:
The only questions worth testing are ones where a natural, honest LLM
answer would list out real brand names -- because that's the only way
to measure whether this brand gets mentioned. A question that a real
shopper would never type, or that an LLM would answer with generic
advice and zero brand names, is USELESS for this purpose, no matter
how specific-sounding it is.

BRAND CONTEXT (the brand name itself must NEVER appear in output):
- Categories: {categories}
- Generic attributes (background context only, secondary priority): {attributes}
- Use cases: {use_cases}
- Who typically buys/uses this category: {personas}
- Price positioning: {price}

RAW SEARCH SIGNALS (for inspiration only, rephrase naturally):
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(signals_to_use))}

GENERATE QUESTIONS IN THESE THREE BUCKETS (this is the PRIMARY structure):

1. AWARENESS -- "best X for Y" recommendation questions
   e.g. "What are the best affordable sneakers for daily wear?"
   e.g. "Best walking shoes for standing all day at work"

2. CONSIDERATION -- brand comparison/evaluation WITHOUT naming any brand
   e.g. "Which sneaker brands offer the best value for daily wear?"
   e.g. "How do budget sneaker brands compare on durability?"
   e.g. "Which brands make the most comfortable walking shoes for work?"

3. DECISION -- buying-decision / value questions
   e.g. "Which sneaker brand offers the best value for money?"
   e.g. "What are some well-reviewed budget sneaker options for daily wear?"
   e.g. "Which brands are known for good quality at an affordable price?"

A smaller fourth bucket is allowed but must stay under 15% of output:

4. ATTRIBUTE-SECONDARY -- only when phrased as "which brands..." around a
   real verified attribute, NEVER as a standalone spec question.
   GOOD: "Which brands make sneakers with good arch support for standing jobs?"
   BAD (reject this pattern entirely): "Does synthetic leather with
   microfiber underlay work well?" -- this is a spec-sheet question, not
   something a shopper types, and an LLM would answer with generic
   material science and zero brand names. NEVER generate this pattern.

HARD RULES:
1. NEVER include the brand name "{brand_name}" or any obvious alias of it.
2. NEVER phrase a question as "BrandX vs BrandY" or name any specific
   competitor either -- comparisons must stay brand-agnostic ("which
   brands...", "how do budget brands compare...").
3. NEVER invent a product attribute, technology name, or spec that is not
   in the attributes list above.
4. Every question must be something a real shopper would actually type
   into a search bar or ask an AI assistant -- not a spec-sheet or
   product-description sentence. If you can't picture a real person
   typing it, don't generate it.
5. Every question should be the KIND of question where a truthful LLM
   answer would naturally list multiple real brand names. If a question
   would just get a generic non-brand-specific answer, it's disqualified.
6. Natural conversational phrasing, max 30 words.
7. Aim for roughly: 35% awareness, 35% consideration, 20% decision,
   10% attribute-secondary.

Return ONLY a JSON array of exactly {target_count} items, no other text:
[
  {{
    "prompt_text": "...",
    "intent_cluster": "informational|comparative|transactional|experiential",
    "prompt_type": "category",
    "funnel_stage": "awareness|consideration|decision|attribute",
    "bio_fields_used": ["attribute:X", "use_case:Y"],
    "source_signal": "..."
  }}
]"""

    try:
        raw_text = call_gemini(
            prompt,
            "You are a prompt engineer for a brand visibility research tool. "
            "Return ONLY a valid JSON array. No text outside the JSON."
        )
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        candidates = json.loads(raw_text)
        print(f"✅ Generated {len(candidates)} raw candidates")
        return candidates
    except Exception as e:
        print(f"❌ Error generating candidates: {e}")
        return []


def _contains_brand_mention(text: str, brand_name: str, aliases: list[str]) -> bool:
    text_lower = text.lower()
    names_to_check = [brand_name] + (aliases or [])
    for name in names_to_check:
        if not name:
            continue
        pattern = r'\b' + re.escape(name.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return True
    return False


def _is_near_duplicate(text: str, seen_texts: list[str], threshold: float = 0.85) -> bool:
    for seen in seen_texts:
        ratio = SequenceMatcher(None, text.lower(), seen.lower()).ratio()
        if ratio >= threshold:
            return True
    return False


def _is_too_generic(text: str, bio_fields_used: list, funnel_stage: str = "") -> bool:
    # Funnel-stage-tagged prompts (awareness/consideration/decision) are
    # validated by their structure (brand-eliciting phrasing), not by
    # how many BIO fields they reference -- a good awareness question
    # like "best affordable sneakers for daily wear" may only tie back
    # to 1-2 fields and that's fine. Only fall back to the field-count
    # check for untagged/attribute-secondary prompts.
    if funnel_stage in ("awareness", "consideration", "decision"):
        if len(text.split()) < 5:
            return True
        return False

    if not bio_fields_used or len(bio_fields_used) < 2:
        return True
    if len(text.split()) < 6:
        return True
    return False


def _contains_coined_term(text: str) -> bool:
    """
    Backstop check -- catches camelCase-style proprietary tech names
    (e.g. 'SpaceWalk', 'AirFlex') that slip into a prompt despite
    genericization. Any such term in a category prompt is disqualifying,
    since it would make the tracked brand trivially/always identifiable.
    """
    return bool(_extract_suspicious_terms(text))


def rule_filter(candidates: list[dict], brand_name: str, brand_aliases: list[str]):
    """
    Deterministic pass. No LLM call. Removes:
    - brand name / alias mentions
    - near-duplicates
    - candidates that don't use >=2 BIO fields (likely generic)
    - candidates that still contain a proprietary/coined term (backstop
      in case genericization missed one)
    Returns (survivors, rejected_log)
    """
    survivors = []
    seen_texts = []
    rejected_log = []

    for c in candidates:
        text = c.get("prompt_text", "")
        if not text:
            continue

        if _contains_brand_mention(text, brand_name, brand_aliases):
            rejected_log.append({"prompt": text, "reason": "brand_name_mentioned"})
            continue

        if _contains_coined_term(text):
            rejected_log.append({"prompt": text, "reason": "proprietary_term_not_genericized"})
            continue

        if _is_near_duplicate(text, seen_texts):
            rejected_log.append({"prompt": text, "reason": "near_duplicate"})
            continue

        if _is_too_generic(text, c.get("bio_fields_used", []), c.get("funnel_stage", "")):
            rejected_log.append({"prompt": text, "reason": "too_generic"})
            continue

        survivors.append(c)
        seen_texts.append(text)

    print(f"✅ Rule filter: {len(survivors)} survived / {len(candidates)} candidates "
          f"({len(rejected_log)} rejected)")
    return survivors, rejected_log


def llm_score_prompts(candidates: list[dict], bio: dict) -> list[dict]:
    """
    Gemini scores each surviving candidate 0-10 on:
    - specificity, naturalness, business_usefulness
    Returns candidates with score + reasoning attached, sorted by score.
    """
    if not candidates:
        return []

    numbered = "\n".join(
        f"{i+1}. {c['prompt_text']}" for i, c in enumerate(candidates)
    )

    prompt = f"""Score each shopper question below on 3 criteria, 0-10 each:

- brand_elicitation: if a truthful, well-informed AI answered this
  question honestly, would it naturally list out multiple real brand
  names? Questions that would get a generic, brand-free answer (e.g.
  spec-sheet material questions like "does synthetic leather work well")
  score LOW. Questions like "best X for Y" or "which brands make good
  X for Z" that naturally prompt a brand list score HIGH. This is the
  MOST IMPORTANT criterion -- a question can't test brand visibility if
  no real answer to it would ever mention brands at all.
- naturalness: would a real shopper actually type/ask this into a
  search bar or AI assistant? Spec-sheet or product-description-style
  phrasing scores LOW even if grammatically correct.
- business_usefulness: is this question still relevant to THIS brand's
  actual category/attributes/audience (not a completely unrelated
  product), so that the brand's absence from the answer would be a
  meaningful, actionable gap for the brand team?

BRAND CATEGORY CONTEXT: {bio.get('product_categories', [])}

QUESTIONS:
{numbered}

Return ONLY a JSON array, same order and length as input, no other text:
[
  {{
    "brand_elicitation": 0-10,
    "naturalness": 0-10,
    "business_usefulness": 0-10,
    "total": 0-30,
    "reasoning": "one short sentence"
  }}
]"""

    try:
        raw_text = call_gemini(
            prompt,
            "You are a strict quality reviewer. Return ONLY a valid JSON array."
        )
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        scores = json.loads(raw_text)

        for c, s in zip(candidates, scores):
            c["review_score"] = s.get("total", 0)
            c["review_breakdown"] = s
        candidates.sort(key=lambda x: x.get("review_score", 0), reverse=True)
        print(f"✅ Scored {len(candidates)} candidates")
        return candidates
    except Exception as e:
        print(f"❌ Error scoring candidates: {e}")
        for c in candidates:
            c["review_score"] = None
        return candidates


def construct_prompts(bio: dict, raw_signals: list[str], target_final_count: int = 50) -> list[dict]:
    """
    Full Stage 5: genericize attributes -> generate -> rule-filter ->
    LLM-score -> return top N.

    Attributes are genericized BEFORE prompt generation so proprietary/
    coined names (e.g. "SpaceWalk soles") never appear in category
    prompts -- a prompt built around a brand's own unique tech name
    trivially always surfaces that brand, which defeats the point of
    a visibility test. The BIO itself (shown to the user for review)
    keeps the real, accurate attribute names -- only the copy fed into
    prompt generation is genericized.
    """
    brand_name    = bio.get("brand_name", "")
    brand_aliases = bio.get("aliases", [])

    generic_attributes = genericize_attributes(
        bio.get("product_attributes", []),
        bio.get("product_categories", [])
    )
    bio_for_prompts = dict(bio)
    bio_for_prompts["product_attributes"] = generic_attributes

    candidates = generate_candidate_prompts(bio_for_prompts, raw_signals, target_count=target_final_count + 30)
    if not candidates:
        return []

    survivors, rejected_log = rule_filter(candidates, brand_name, brand_aliases)
    if not survivors:
        print("⚠️  All candidates rejected by rule filter -- check BIO quality / regenerate")
        return []

    scored = llm_score_prompts(survivors, bio)

    final = scored[:target_final_count]
    print(f"✅ Final prompt corpus: {len(final)} prompts "
          f"(from {len(candidates)} generated, {len(rejected_log)} rule-rejected)")

    return final


# ══════════════════════════════════════════════
# BRAND SOURCE URL MATCHING
# ──────────────────────────────────────────────
# Given the list of citation URLs a grounded response actually used,
# figure out which ones (if any) are specifically about the tracked
# brand -- so "brand was mentioned" comes with "here's where."
# ══════════════════════════════════════════════

def find_brand_source_urls(
    citation_urls: list[dict],
    brand_domain: str,
    brand_name: str,
    brand_aliases: list[str] = None,
    grounding_supports: list[dict] = None,
) -> list[dict]:
    """
    Finds the citation(s) that actually back the SENTENCE mentioning the
    brand, not just any source the response happened to use.

    Priority order:
    1. SEGMENT-LEVEL MATCH (most accurate) -- if grounding_supports is
       provided (Gemini), find the text segment(s) that mention the
       brand name/alias, and return the citation chunks tied to THAT
       segment specifically. This correctly handles the common case
       where a grounded answer cites a third-party roundup article
       (e.g. "Top 10 Sneaker Brands") that mentions the brand within
       its text -- the citation's own domain/title won't contain the
       brand name, but the specific sentence it backs does.
    2. CHAR-RANGE MATCH (OpenAI) -- if citation_urls entries have
       start_index/end_index (character offsets into the raw response),
       and brand_name appears within that character range, it's a match.
    3. DOMAIN/TITLE FALLBACK -- if neither of the above applies (or
       finds nothing), fall back to checking whether the citation's own
       domain or title contains the brand's domain/name. Weakest signal,
       but better than nothing when structured data isn't available.
    """
    if not citation_urls:
        return []

    brand_domain_clean = (brand_domain or "").lower().replace("www.", "").strip()
    brand_name_lower = (brand_name or "").lower()
    names_to_check = [brand_name_lower] + [a.lower() for a in (brand_aliases or []) if a]

    def _mentions_brand(text: str) -> bool:
        text_lower = (text or "").lower()
        return any(name and name in text_lower for name in names_to_check)

    # ── 1. Segment-level match (Gemini grounding_supports) ──
    if grounding_supports:
        matched_indices = set()
        for support in grounding_supports:
            if _mentions_brand(support.get("text", "")):
                matched_indices.update(support.get("chunk_indices", []))

        if matched_indices:
            matches = []
            for idx in matched_indices:
                if 0 <= idx < len(citation_urls):
                    c = citation_urls[idx]
                    matches.append({
                        "title": c.get("title", ""),
                        "url": c.get("uri") or c.get("url", ""),
                        "matched_by": "segment",
                    })
            if matches:
                seen_urls = set()
                deduped = []
                for m in matches:
                    if m["url"] not in seen_urls:
                        seen_urls.add(m["url"])
                        deduped.append(m)
                return deduped

    # ── 2. Char-range match (OpenAI annotations) ──
    char_range_matches = []
    for c in citation_urls:
        start = c.get("start_index")
        end = c.get("end_index")
        if start is not None and end is not None:
            # Note: caller must have already sliced raw_text[start:end]
            # into c.get("_covered_text") before calling this, OR we
            # rely on the domain/title fallback below if that wasn't done.
            covered = c.get("_covered_text", "")
            if covered and _mentions_brand(covered):
                char_range_matches.append({
                    "title": c.get("title", ""),
                    "url": c.get("uri") or c.get("url", ""),
                    "matched_by": "char_range",
                })
    if char_range_matches:
        return char_range_matches

    # ── 3. Domain/title fallback ──
    matches = []
    for c in citation_urls:
        url = (c.get("uri") or c.get("url") or "").lower()
        title = (c.get("title") or "").lower()

        domain_match = bool(brand_domain_clean) and brand_domain_clean in url
        name_in_title = bool(brand_name_lower) and brand_name_lower in title

        if domain_match or name_in_title:
            matches.append({
                "title": c.get("title", ""),
                "url": c.get("uri") or c.get("url", ""),
                "matched_by": "domain" if domain_match else "title",
            })

    return matches


# ══════════════════════════════════════════════
# STAGE 7 — RESPONSE PARSING (unchanged)
# ══════════════════════════════════════════════

def parse_response(
    raw_response:  str,
    brand_name:    str,
    brand_aliases: list[str] = []
) -> dict:
    """Parse a raw AI engine response using Gemini."""

    prompt = f"""Analyze this AI engine response for brand mentions and competitors.

TRACKED BRAND: {brand_name}
KNOWN ALIASES: {", ".join(brand_aliases) if brand_aliases else "none"}

AI RESPONSE TO ANALYZE:
{raw_response[:3000]}

Return ONLY this JSON object:
{{
    "brand_mentioned": true or false,
    "brand_cited": true or false,
    "mention_form": "exact or fuzzy or indirect or none",
    "mention_position": 1,
    "sentiment": "positive or neutral or negative or not_applicable",
    "competing_brands": [
        {{"brand_name": "BrandX", "mention_position": 1, "cited": true}}
    ]
}}

RULES:
- brand_mentioned: true if brand appears in any form
- brand_cited: true only if a URL reference to the brand appears
- mention_form: exact/fuzzy/indirect/none
- competing_brands: ALL other brands mentioned
- sentiment: only where brand IS mentioned, else "not_applicable"
"""

    try:
        raw_text = call_gemini(
            prompt,
            "You are a brand analyst. Return ONLY valid JSON. No text outside the JSON."
        )
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)

    except Exception as e:
        print(f"❌ Error parsing response: {e}")
        return {
            "brand_mentioned":  False,
            "brand_cited":      False,
            "mention_form":     "none",
            "mention_position": None,
            "sentiment":        "not_applicable",
            "competing_brands": [],
        }
