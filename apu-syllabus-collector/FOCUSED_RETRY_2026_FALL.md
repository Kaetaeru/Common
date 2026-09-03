# AY2026 Fall focused retry

This collector should use `data/collector_state.json` as the authoritative target list for focused retry. The current user-verified state contains 26 unresolved APM Class codes. Use the UI action `실패 N개 집중 재시도`; it queues only Class codes currently present in `failed` and excludes any Class already present in `data/syllabus_links.json`.

Focused retry remains Class-code-only. It never falls back to Subject Name search.
