"""One-off probe: where Advanced ratios live in Groww HTML (dev utility)."""

import re
import sys

import requests

from policy.loader import load_allowlist

url = load_allowlist()[int(sys.argv[1]) if len(sys.argv) > 1 else 2]
text = requests.get(
    url, headers={"User-Agent": "MF-FAQ-Assistant/1.0"}, timeout=60
).text
needles = [
    "Advanced ratios",
    "top_5",
    "top5",
    "top_20",
    "top20",
    "pe_ratio",
    "pb_ratio",
    "P/E Ratio",
    "P/B Ratio",
    "sharpe_ratio",
    "sortino",
]
for n in needles:
    print(n, "->", bool(re.search(re.escape(n), text, re.I)))

idx = text.lower().find("sharpe_ratio")
if idx >= 0:
    print("\ncontext:", text[idx - 80 : idx + 200].replace("\n", " "))
