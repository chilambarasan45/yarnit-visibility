"""
fix_api_imports_v2.py

Safe to run even if files were already partially patched (e.g. by a
previous attempt) -- de-duplicates instead of blindly inserting, so it
can't create the "Identifier 'api' has already been declared" error.

Run from the project root:
    python fix_api_imports_v2.py
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

    # 1. Remove EVERY existing axios import line (any quote style)
    content = re.sub(r"^\s*import axios from ['\"]axios['\"];\s*\n", "", content, flags=re.MULTILINE)

    # 2. Remove EVERY existing "import api from '../api';" line -- we'll
    #    add back exactly ONE at the end. This is what makes the script
    #    safe to re-run: no matter how many duplicates exist right now,
    #    they all get removed first.
    content = re.sub(r"^\s*import api from ['\"]\.\./api['\"];\s*\n", "", content, flags=re.MULTILINE)

    # 3. Remove the hardcoded API constant line, any quote style
    content = re.sub(r"^\s*const API\s*=\s*['\"]http://127\.0\.0\.1:8000/api['\"];\s*\n", "", content, flags=re.MULTILINE)

    # 4. Convert every axios.method( call to api.method(
    content = re.sub(r"\baxios\.(get|post|put|delete|patch)\(", r"api.\1(", content)

    # 5. Strip "${API}" out of template literals
    content = re.sub(r"\$\{API\}", "", content)

    # 6. Insert exactly ONE "import api from '../api';" right after the
    #    first import line (the React import), if the file actually
    #    uses `api.` anywhere.
    if re.search(r"\bapi\.(get|post|put|delete|patch)\(", content):
        lines = content.split("\n")
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import "):
                insert_at = i + 1
        lines.insert(insert_at, "import api from '../api';")
        content = "\n".join(lines)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated: {filepath}")
    else:
        print(f"No changes needed: {filepath}")

print("\nDone.")
