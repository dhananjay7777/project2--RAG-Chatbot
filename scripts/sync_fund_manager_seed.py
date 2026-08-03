"""Backward-compatible entrypoint — prefer scripts/sync_fact_seed_volatile.py. """

from scripts.sync_fact_seed_volatile import main

if __name__ == "__main__":
    main()
