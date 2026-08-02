# Corpus Registry — Frozen Groww Scheme Pages

> Companion to [`Architecture.md`](./Architecture.md).
> **Hard rule:** these five URLs are the entire corpus. No other URL may be fetched,
> indexed, cited, or used as a refusal / performance-redirect link.

Snapshot date for seed values below: **24 Jul 2026** (NAV-as-of on the captured pages).
Values must be re-verified at ingest time; this matrix is a design-time seed, not a
runtime source of truth.

---

## 1. Locked URL Allowlist

Copy verbatim into `policy/source_allowlist.yaml` and `policy/source_registry.yaml`.

| source_id | scheme_name | amc | url |
| --- | --- | --- | --- |
| `groww-nippon-india-value-fund-direct-growth` | Nippon India Value Fund Direct Growth | Nippon India Mutual Fund | https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth |
| `groww-tata-multi-asset-allocation-fund-direct-growth` | Tata Multi Asset Allocation Fund Direct Growth | Tata Mutual Fund | https://groww.in/mutual-funds/tata-multi-asset-allocation-fund-direct-growth |
| `groww-kotak-multi-asset-allocation-fund-direct-growth` | Kotak Multi Asset Allocation Fund Direct Growth | Kotak Mahindra Mutual Fund | https://groww.in/mutual-funds/kotak-multi-asset-allocation-fund-direct-growth |
| `groww-franklin-india-multi-cap-fund-direct-growth` | Franklin India Multi Cap Fund Direct Growth | Franklin Templeton Mutual Fund | https://groww.in/mutual-funds/franklin-india-multi-cap-fund-direct-growth |
| `groww-samco-mid-cap-fund-direct-growth` | Samco Mid Cap Fund Direct Growth | Samco Mutual Fund | https://groww.in/mutual-funds/samco-mid-cap-fund-direct-growth |

```yaml
# policy/source_allowlist.yaml
allowlist_mode: exact_url
urls:
  - https://groww.in/mutual-funds/nippon-india-value-fund-direct-growth
  - https://groww.in/mutual-funds/tata-multi-asset-allocation-fund-direct-growth
  - https://groww.in/mutual-funds/kotak-multi-asset-allocation-fund-direct-growth
  - https://groww.in/mutual-funds/franklin-india-multi-cap-fund-direct-growth
  - https://groww.in/mutual-funds/samco-mid-cap-fund-direct-growth
```

---

## 2. In-Scope Fact Keys

| fact_key | Answerable? | Notes |
| --- | --- | --- |
| `expense_ratio` | Yes | Hero metric on every page |
| `exit_load` | Yes | Dedicated section; use current (latest) rule text |
| `min_sip` | Yes | Under Minimum investments |
| `min_lumpsum` | Yes | Min. for 1st investment |
| `risk_rating` | Yes | Groww risk label (e.g. Very High Risk) — proxy for riskometer |
| `category` | Yes | e.g. Equity Value Oriented, Hybrid Multi Asset Allocation |
| `aum` | Yes | Fund size on page (scheme AUM, not AMC total AUM) |
| `nav` | Yes | Latest NAV + as-of date; do not invent history |
| `benchmark` | Yes if present | Null on some pages (Tata / Kotak currently blank) |
| `fund_manager` | Yes | Current manager name(s) |
| `launch_date` | Yes | From About / Fund house block |
| `investment_objective` | Yes | About section prose |
| `stamp_duty` | Yes | Common text on pages (0.005%) |
| `tax_implication_text` | Yes | Verbatim Groww tax blurb only — no computation |
| `elss_lock_in` | **No** | No ELSS scheme in corpus → `NO_ANSWER` |
| `statement_download` | **No** | Not on these pages → `NO_ANSWER` |
| `capital_gains_download` | **No** | Not on these pages → `NO_ANSWER` |
| `returns_*` | **No** | Present on page but stripped; route `PERFORMANCE_REDIRECT` |
| `holdings` | **No** | Present on page but stripped from index |
| `advanced_ratios_*` | **Partial** | Groww shows an **Advanced ratios** panel on the live site (Top 5 / Top 20 concentration, P/E, P/B; Alpha/Beta/Sharpe/Sortino often **`--`** when undisclosed). **Not** in current markdown bootstrap artifacts. **Live HTML** embeds static JSON (`sharpe_ratio`, `beta`, `pe_ratio`, etc.) — Phase 2 must parse from `make ingest` HTML, not invent values. When Groww displays `--`, answer **not disclosed on source** (still one citation). Distinct from **`expense_ratio` (TER)**. |

---

## 2b. Advanced ratios on Groww vs our corpus

| Layer | What you see | In our repo today |
| --- | --- | --- |
| **Groww UI** | “Advanced ratios” card: Top 5 %, Top 20 %, P/E, P/B; Alpha, Beta, Sharpe, Sortino (often **`--`** = not provided for that scheme) | Same as browser when you open the five URLs |
| **Bootstrap markdown** (`data/bootstrap/snapshots`, `.md` in `data/raw/`) | — | **Panel text not captured** (holdings/hero metrics only) |
| **Live HTML** (`make ingest`) | UI labels may still be client-rendered | **Embedded JSON** in page source (e.g. `"sharpe_ratio"`, `"beta"`, `"pe_ratio"`) — treat as static payload for Phase 2 extraction |

**Assistant behaviour (planned Phase 2+):**

- Answer **Top 5 / Top 20 / P/E / P/B** when present on the cited Groww page.
- For **Alpha / Beta / Sharpe / Sortino**: if the source shows **`--`**, respond that Groww does not disclose the value (do not substitute JSON from a different widget unless Phase 2 proves it is the same disclosure).

Re-check stored artifacts:

```powershell
python -m ingest.acquisition audit
make ingest          # refresh raw HTML before Phase 2 parsing
```

---

## 3. Seed Fact Card Matrix

### Nippon India Value Fund Direct Growth

| fact_key | seed value_text |
| --- | --- |
| expense_ratio | 1.27% |
| exit_load | For units more than 10% of the investments, an exit load of 1% if redeemed within 12 months. |
| min_sip | ₹100 |
| min_lumpsum | ₹500 |
| risk_rating | Very High Risk |
| category | Equity — Value Oriented |
| aum | ₹8,962.36 Cr |
| nav | ₹244.42 (as of 24 Jul 2026) |
| benchmark | NIFTY 500 Total Return Index |
| launch_date | 30 Jun 1995 |

### Tata Multi Asset Allocation Fund Direct Growth

| fact_key | seed value_text |
| --- | --- |
| expense_ratio | 0.62% |
| exit_load | Exit load of 0.50%, if redeemed within 30 days. |
| min_sip | ₹100 |
| min_lumpsum | ₹5,000 |
| risk_rating | Very High Risk |
| category | Hybrid — Multi Asset Allocation |
| aum | ₹5,154.54 Cr |
| nav | ₹27.95 (as of 24 Jul 2026) |
| benchmark | null (page shows blank) |
| launch_date | 30 Jun 1995 |

### Kotak Multi Asset Allocation Fund Direct Growth

| fact_key | seed value_text |
| --- | --- |
| expense_ratio | 0.61% |
| exit_load | Exit Load for units in excess of 30% of the investment, 1% will be charged for redemption within 1 year. |
| min_sip | ₹100 |
| min_lumpsum | ₹100 |
| risk_rating | Very High Risk |
| category | Hybrid — Multi Asset Allocation |
| aum | ₹14,308.51 Cr |
| nav | ₹16.17 (as of 24 Jul 2026) |
| benchmark | null (page shows blank) |
| launch_date | 05 Aug 1994 |

### Franklin India Multi Cap Fund Direct Growth

| fact_key | seed value_text |
| --- | --- |
| expense_ratio | 0.93% |
| exit_load | Exit load of 1%, if redeemed within 1 year. |
| min_sip | ₹500 |
| min_lumpsum | ₹5,000 |
| risk_rating | Very High Risk |
| category | Equity — Multi Cap |
| aum | ₹5,029.48 Cr |
| nav | ₹10.94 (as of 24 Jul 2026) |
| benchmark | Nifty 500 Multicap 50:25:25 Total Return Index |
| launch_date | 19 Feb 1996 |

### Samco Mid Cap Fund Direct Growth

| fact_key | seed value_text |
| --- | --- |
| expense_ratio | 1.87% |
| exit_load | Exit load of 1%, if redeemed within 30 days. |
| min_sip | ₹250 |
| min_lumpsum | ₹5,000 |
| risk_rating | Very High Risk |
| category | Equity — Mid Cap |
| aum | ₹78.64 Cr |
| nav | ₹9.79 (as of 24 Jul 2026) |
| benchmark | NIFTY Midcap 150 Total Return Index |
| launch_date | 14 Sep 2021 |

> Note: Samco's About blurb mentions a larger AMC-level AUM figure. Fact Cards must use
> the **scheme** fund-size figure from the hero metrics (`₹78.64 Cr`), not the fund-house
> total. Groundedness checks should prefer the hero block for `aum`.

---

## 4. Sections to Strip Before Indexing

Do not index these regions from any of the five pages:

- Global nav, stock/F&O product menus, app download chrome, site footer
- Return calculator and any historic-returns tables
- Returns and rankings / category average / rank tables
- Holdings tables
- "Also manages these schemes" and related-fund link farms
- Compare-funds and screener promos
- Blog / calculator / credit product cross-sells

---

## 5. Citation Policy

| Route | Citation URL |
| --- | --- |
| FACTUAL | The single Groww scheme page that supports the claim |
| REFUSAL | The scheme page named in the query if identifiable; else any one of the five (prefer Nippon as default) |
| PERFORMANCE_REDIRECT | The scheme page named in the query (numeral-free body) |
| NO_ANSWER | Optional: scheme page if identifiable; still exactly one URL from the five |
| CLARIFY | Same as NO_ANSWER |

Never cite a sixth URL.
