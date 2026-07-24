"""
tests/eval_agents.py

A SMALL EVAL SUITE for the AI agents in this pipeline.

WHAT "EVAL" MEANS HERE:
An eval is different from a normal unit test. A unit test checks "does
this function return the right data type / not crash." An eval checks
"is the AI agent's actual JUDGMENT good" -- e.g. did it correctly reject
a bad prompt, did it correctly avoid hallucinating, did it correctly
identify a brand-eliciting question. Since LLM outputs aren't 100%
deterministic, evals run against a small set of FIXED, KNOWN test cases
and score pass/fail against expected behavior, rather than expecting an
exact string match.

WHY THIS MATTERS FOR THIS PROJECT SPECIFICALLY:
Every fix made in this project so far (hallucination verification, brand
name leakage, generic-question quality, brand-elicitation scoring) was a
JUDGMENT problem, not a crash. This eval suite turns "I fixed the
hallucination issue" from a claim into something you can re-run and show
a number for.

HOW TO RUN:
    python -m tests.eval_agents

This does NOT call real LLMs by default (keeps it fast, free, and
deterministic for repeated runs) -- it tests the DETERMINISTIC parts of
the pipeline (rule_filter, hallucination verification, source matching)
directly, since those are the parts that must behave correctly every
single time regardless of what the LLM outputs. A second section shows
how to extend this to live LLM calls when you want to eval the
LLM-judgment parts too.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.claude_service import (
    rule_filter,
    _contains_brand_mention,
    _quote_appears_in_source,
    _contains_coined_term,
    find_brand_source_urls,
)

results = {"passed": 0, "failed": 0, "details": []}


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results["passed" if condition else "failed"] += 1
    results["details"].append((status, name, detail))
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail and not condition else ""))


# ══════════════════════════════════════════════
# EVAL 1 — Brand name leakage detection
# ══════════════════════════════════════════════
print("\n=== EVAL 1: Brand name leakage ===")

check(
    "Detects exact brand name in prompt",
    _contains_brand_mention("Is Comet the best sneaker brand?", "Comet", []) == True,
)
check(
    "Does NOT false-positive on unrelated word containing brand as substring",
    _contains_brand_mention("Which brands make cometary-grade rubber?", "Comet", []) == False,
    "word-boundary check should prevent 'cometary' matching 'comet'",
)
check(
    "Detects brand alias",
    _contains_brand_mention("Are CometShoes good for daily wear?", "Comet", ["CometShoes"]) == True,
)
check(
    "Clean generic prompt passes with no brand mention",
    _contains_brand_mention("Which sneaker brands offer the best value?", "Comet", []) == False,
)


# ══════════════════════════════════════════════
# EVAL 2 — Hallucination verification (quote matching)
# ══════════════════════════════════════════════
print("\n=== EVAL 2: Hallucination verification ===")

SOURCE_TEXT = (
    "Our sneakers feature a lightweight breathable mesh upper and a "
    "cushioned rubber sole designed for all-day comfort."
)

check(
    "Accepts a real, exact quote from source",
    _quote_appears_in_source("lightweight breathable mesh upper", SOURCE_TEXT) == True,
)
check(
    "Rejects a fabricated quote sharing only common words with source",
    _quote_appears_in_source(
        "our sneakers use a proprietary AeroGlide suspension system for comfort",
        SOURCE_TEXT
    ) == False,
    "shares 'sneakers'/'comfort' with source but the claim itself is invented",
)
check(
    "Rejects an empty/too-short quote",
    _quote_appears_in_source("ok", SOURCE_TEXT) == False,
)


# ══════════════════════════════════════════════
# EVAL 3 — Coined/proprietary term detection (backstop)
# ══════════════════════════════════════════════
print("\n=== EVAL 3: Proprietary term backstop ===")

check(
    "Flags a camelCase-style coined term in a prompt",
    _contains_coined_term("Do 3-layer SpaceWalk soles improve comfort?") == True,
)
check(
    "Does NOT flag ordinary generic language",
    _contains_coined_term("What are the best cushioned sneakers for daily wear?") == False,
)


# ══════════════════════════════════════════════
# EVAL 4 — Rule filter end-to-end (combines all checks above)
# ══════════════════════════════════════════════
print("\n=== EVAL 4: Rule filter (deterministic pipeline stage) ===")

candidates = [
    {"prompt_text": "Is Comet the best sneaker brand for daily wear?", "bio_fields_used": ["a", "b"], "funnel_stage": "awareness"},
    {"prompt_text": "Which sneaker brands offer the best value for daily wear?", "bio_fields_used": ["a", "b"], "funnel_stage": "awareness"},
    {"prompt_text": "Which sneaker brands offer the best value for daily wear?", "bio_fields_used": ["a", "b"], "funnel_stage": "awareness"},  # dup
    {"prompt_text": "Do 3-layer SpaceWalk soles improve comfort?", "bio_fields_used": ["a", "b"], "funnel_stage": "attribute"},
    {"prompt_text": "Which brands make comfortable sneakers with good arch support?", "bio_fields_used": ["a", "b"], "funnel_stage": "consideration"},
]

survivors, rejected = rule_filter(candidates, "Comet", [])

check("Rejects the brand-name-leaking prompt", not any("Comet" in s["prompt_text"] for s in survivors))
check("Rejects the near-duplicate (only 1 of the 2 identical prompts survives)",
      sum(1 for s in survivors if "best value for daily wear" in s["prompt_text"]) == 1)
check("Rejects the coined-term prompt (SpaceWalk)", not any("SpaceWalk" in s["prompt_text"] for s in survivors))
check("Keeps the two genuinely good prompts", len(survivors) == 2)
check("Rejection log has an entry for each rejected candidate", len(rejected) == 3)


# ══════════════════════════════════════════════
# EVAL 5 — Source matching (segment-level vs fallback)
# ══════════════════════════════════════════════
print("\n=== EVAL 5: Source URL matching ===")

citation_urls = [
    {"title": "Best Running Shoes 2026", "uri": "https://runningblog.com/best-shoes"},
    {"title": "Top 10 Sneaker Brands India", "uri": "https://sneakerlist.in/top10"},
]
grounding_supports = [
    {"text": "Popular options include Bata and Liberty.", "chunk_indices": [0]},
    {"text": "Comet is also a well-known choice for cushioned sneakers.", "chunk_indices": [1]},
]

matches = find_brand_source_urls(
    citation_urls, "wearcomet.com", "Comet",
    brand_aliases=[], grounding_supports=grounding_supports, brand_was_mentioned=True,
)
check(
    "Segment-level match finds the correct third-party citation, not domain-based guessing",
    len(matches) == 1 and "sneakerlist.in" in matches[0]["url"],
)

matches_none = find_brand_source_urls(
    citation_urls, "wearcomet.com", "Comet",
    brand_aliases=[], grounding_supports=[], brand_was_mentioned=False,
)
check(
    "Never fabricates a source when the brand was not actually mentioned",
    matches_none == [],
)


# ══════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════
print("\n" + "=" * 50)
print(f"RESULTS: {results['passed']} passed, {results['failed']} failed "
      f"({results['passed']}/{results['passed'] + results['failed']})")
if results["failed"] > 0:
    print("\nFailed checks:")
    for status, name, detail in results["details"]:
        if status == "FAIL":
            print(f"  - {name}" + (f" ({detail})" if detail else ""))
print("=" * 50)


# ══════════════════════════════════════════════
# EXTENDING TO LIVE LLM EVALS (not run by default)
# ──────────────────────────────────────────────
# The checks above test the deterministic guardrails around the LLM
# calls -- the part that must be 100% reliable. To also eval the LLM's
# own judgment quality (e.g. "does the Reviewer agent actually score
# brand-eliciting questions higher than spec-sheet questions"), the
# same pattern extends naturally:
#
#   from app.services.claude_service import llm_score_prompts
#   test_prompts = [
#       {"prompt_text": "Which brands make the best running shoes?"},  # should score HIGH
#       {"prompt_text": "Does synthetic leather work well?"},          # should score LOW
#   ]
#   scored = llm_score_prompts(test_prompts, {"product_categories": ["sneakers"]})
#   assert scored[0]["review_score"] > scored[1]["review_score"]
#
# This costs real API calls, so it's kept separate from the free/fast
# suite above -- run it manually when you want to validate LLM judgment
# quality specifically, not on every code change.
# ══════════════════════════════════════════════