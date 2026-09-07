import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Customer, ScanRun
from app.services.engine import decide

def scan_customers(db:Session,limit:int=100,after:str|None=None)->dict:
    scan=ScanRun(scan_id=str(uuid.uuid4()),cursor=after); db.add(scan); db.commit()
    q=select(Customer).order_by(Customer.user_id).limit(limit)
    if after: q=q.where(Customer.user_id>after)
    rows=list(db.scalars(q)); candidates=0
    for row in rows:
        result=decide(db,row.user_id); candidates += int(result["action_type"]!="take_no_action"); scan.cursor=row.user_id; scan.processed+=1
    scan.candidates=candidates; scan.status="completed"; scan.completed_at=datetime.now(timezone.utc).isoformat(); db.commit()
    return {"scan_id":scan.scan_id,"processed":scan.processed,"candidates":candidates,"next_cursor":scan.cursor,"has_more":len(rows)==limit}
