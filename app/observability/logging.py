import json, logging
from datetime import datetime, timezone

logger=logging.getLogger("growth_engine")
if not logger.handlers:
    handler=logging.StreamHandler(); handler.setFormatter(logging.Formatter("%(message)s")); logger.addHandler(handler); logger.setLevel(logging.INFO)

def log_event(name:str,correlation_id:str,**fields)->None:
    logger.info(json.dumps({"timestamp":datetime.now(timezone.utc).isoformat(),"event":name,"correlation_id":correlation_id,**fields},default=str))
