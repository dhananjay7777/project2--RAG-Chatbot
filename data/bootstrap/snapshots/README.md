# Offline Groww page snapshots (development bootstrap only)

Place one file per scheme slug, matching the upload naming convention:

- `nippon-india-value-fund-direct-growth-0.md`
- `tata-multi-asset-allocation-fund-direct-growth-1.md`
- etc.

Or exact `{slug}.md` / `{slug}.html`.

Bootstrap with:

```powershell
python -m ingest.acquisition bootstrap --snapshot-dir data/bootstrap/snapshots
```

Snapshot runs set `promotion_ready: false`. Re-fetch live before demo/eval promotion.
