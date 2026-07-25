"""
fix_api_imports.py

Run this once from the project root:
    python fix_api_imports.py

Fixes every frontend component to use the shared api.js instance
instead of plain axios + a hardcoded localhost URL.
"""

import re
import os

files = [
    "frontend/src/components/BrandSetup.js",
    "frontend/src/components/Dashboard.js",
    "frontend/src/components/Overview.js",
    "frontend/src/components/GeoBreakdown.js",
    "frontend/src/components/EngineBreakdown.js",
    "frontend/src/components/Competitors.js",
    "frontend/src/components/PromptSelector.js",
    "frontend/src/components/PipelineFlow.js",
    "frontend/src/components/RunHistory.js",
    "frontend/src/components/TrendChart.js",
    "frontend/src/components/ExecutiveSummary.js",
]

for filepath in files:
    if not os.path.exists(filepath):
        print(f"NOT FOUND (skipped): {filepath}")
        continue

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # 1. Swap the axios import for the shared api instance
    content = re.sub(r"import axios from 'axios';\n?", "import api from '../api';\n", content)

    # 2. Remove the hardcoded API constant line (any quote style, any whitespace)
    content = re.sub(r"const API\s*=\s*['\"]http://127\.0\.0\.1:8000/api['\"];\n?", "", content)

    # 3. Change every axios.get/post/put/delete call to api.<method>
    content = re.sub(r"\baxios\.(get|post|put|delete|patch)\(", r"api.\1(", content)

    # 4. Strip "${API}" out of template literals -- api.js's baseURL already
    #    includes "/api", so what's left (e.g. `/brands`) resolves correctly
    #    as a relative path against that baseURL.
    content = re.sub(r"\$\{API\}", "", content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated: {filepath}")
    else:
        print(f"No changes needed: {filepath}")

print("\nDone. Now run the verification checks.")
