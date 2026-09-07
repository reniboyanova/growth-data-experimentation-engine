# Local end-to-end demo

Run `python -m app.scripts.demo` after `python -m app.scripts.init_db`. It creates synthetic signup and checkout events, grants synthetic consent, creates a checkout-recovery candidate, renders a deterministic draft, approves it and executes it through the fake provider. Re-run to observe event and action idempotency.

Expected final line contains `"simulated": True` and a `fake-...` provider id. This proves application flow, not delivery or business uplift.
