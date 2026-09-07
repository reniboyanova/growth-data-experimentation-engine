import os
from pathlib import Path

TEST_DB = Path(__file__).parent / ".test-growth.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["EXECUTION_MODE"] = "simulation"

def pytest_sessionfinish(session, exitstatus):
    from app.database import engine
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)
