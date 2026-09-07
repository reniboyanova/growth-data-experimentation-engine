# Local runbook

- Database locked: stop duplicate dev servers; never delete the production database.
- Stuck pending action: inspect `/actions?status=pending`, state freshness, consent and support events.
- Provider ambiguity: stop execution and reconcile by provider ID before retry.
- Backup: stop writers and copy `growth.db`; restore only to a new path, point `DATABASE_URL` to it, then run tests.
- Migration rollback: restore the backup and previous application version. Add Alembic before changing a real persisted schema.
- Emergency stop: keep `EXECUTION_MODE=simulation`; a future live adapter must also enforce `SEND_KILL_SWITCH` and recipient allowlist.
- Tests: pytest always uses `tests/.test-growth.db`; a failing test must never open `growth.db`.
- Migrations: install `requirements-dev.txt`, back up the DB, then use `alembic stamp 0001` for an existing baseline and create reviewed revisions for later changes.
