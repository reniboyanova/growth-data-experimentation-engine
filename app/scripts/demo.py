from fastapi.testclient import TestClient
from app.main import app

def main():
    c=TestClient(app); user="demo-user"
    for eid,name in [("demo-signup","user_signed_up"),("demo-checkout","checkout_started")]:
        print(c.post("/events",json={"event_id":eid,"user_id":user,"event_name":name,"timestamp":"2026-09-01T10:00:00Z","source":"demo","properties":{}}).json())
    c.post(f"/customers/{user}/consents",json={"status":"granted","source":"demo","timestamp":"2026-09-01T09:00:00Z"})
    decision=c.post(f"/decisions/evaluate/{user}").json(); print("DECISION",decision)
    action=decision["action_id"]; print("DRAFT",c.post(f"/actions/{action}/draft").json())
    print("APPROVAL",c.post(f"/actions/{action}/approve",json={"approver":"demo-reviewer"},headers={"x-role":"approver"}).json())
    print("EXECUTION",c.post(f"/actions/{action}/execute",headers={"x-role":"executor"}).json())
if __name__=="__main__": main()
