import uuid
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Customer, Identity

@dataclass(frozen=True)
class IdentityResult:
    status: str
    user_id: str | None
    matches: tuple[str, ...] = ()

def resolve_customer(db:Session, identifiers:dict[str,str], create:bool=False)->IdentityResult:
    matches=set()
    for namespace,external_id in identifiers.items():
        row=db.scalar(select(Identity).where(Identity.namespace==namespace,Identity.external_id==external_id))
        if row: matches.add(row.user_id)
    if len(matches)>1: return IdentityResult("ambiguous",None,tuple(sorted(matches)))
    if len(matches)==1:
        user_id=next(iter(matches))
        for namespace,external_id in identifiers.items():
            existing=db.scalar(select(Identity).where(Identity.namespace==namespace,Identity.external_id==external_id))
            if not existing: db.add(Identity(user_id=user_id,namespace=namespace,external_id=external_id,verified=False))
        db.commit(); return IdentityResult("resolved",user_id)
    if not create: return IdentityResult("not_found",None)
    user_id=f"customer-{uuid.uuid4()}"; db.add(Customer(user_id=user_id))
    for namespace,external_id in identifiers.items(): db.add(Identity(user_id=user_id,namespace=namespace,external_id=external_id,verified=False))
    db.commit(); return IdentityResult("created",user_id)
