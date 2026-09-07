from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import ExperimentAssignment

def experiment_results(db:Session,experiment_id:str,minimum_sample:int=30)->dict:
    rows=list(db.scalars(select(ExperimentAssignment).where(ExperimentAssignment.experiment_id==experiment_id)))
    groups=defaultdict(list)
    for row in rows: groups[row.variant].append(row)
    def stats(name):
        mature=[r for r in groups[name] if r.exposed_at is not None]; converted=sum(r.converted for r in mature)
        return {"users":len(mature),"converted":converted,"rate":converted/len(mature) if mature else 0.0}
    control,treatment=stats("control"),stats("treatment"); absolute=treatment["rate"]-control["rate"]
    return {"control":control,"treatment":treatment,"absolute_uplift":absolute,
        "relative_uplift":absolute/control["rate"] if control["rate"] else None,
        "status":"ready" if min(control["users"],treatment["users"])>=minimum_sample else "insufficient_data"}
