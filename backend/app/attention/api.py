import json
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import AttentionConfigAudit, AttentionEvent, AttentionRunLog, Receipt
from .engine import REFERENCE_FIELDS, SEVERITY_RANK, config_dict, evaluate, get_config

router = APIRouter(prefix="/api/v1/attention", tags=["attention"])
evaluation_lock = Lock()

def event_dict(event):
    return {"id":event.id,"event_time":event.event_time,"supplier_id":event.supplier_id,"supplier_code":event.supplier.supplier_code,"supplier_name":event.supplier.supplier_name,"material_id":event.material_id,"material_code":event.material.material_code,"material_name":event.material.material_name,"attribute_id":event.attribute_id,"attribute_code":event.attribute.attribute_code,"attribute_name":event.attribute.attribute_name,"data_type":event.attribute.data_type,"reference_id":event.reference_id,"receipt_id":event.receipt_id,"sample_id":event.sample_id,"test_result_id":event.test_result_id,"specification_id":event.specification_id,"rule_code":event.rule_code,"severity":event.severity,"status":event.status,"observed_value":event.observed_value,"message":event.message,"lsl":float(event.lsl) if event.lsl is not None else None,"usl":float(event.usl) if event.usl is not None else None,"target_value":event.target_value,"baseline_mean":float(event.baseline_mean) if event.baseline_mean is not None else None,"baseline_sigma":float(event.baseline_sigma) if event.baseline_sigma is not None else None,"baseline_n":event.baseline_n,"config_version":event.config_version,"evidence":json.loads(event.rule_evidence_json),"acknowledged_at":event.acknowledged_at,"acknowledged_by":event.acknowledged_by}

def event_query(db):
    return db.query(AttentionEvent).options(joinedload(AttentionEvent.supplier),joinedload(AttentionEvent.material),joinedload(AttentionEvent.attribute))

@router.get("/config")
def read_config(db:Session=Depends(get_db)): return config_dict(get_config(db))

@router.put("/config")
def update_config(payload:dict=Body(...),db:Session=Depends(get_db)):
    current=get_config(db); before=config_dict(current)
    allowed={"enabled","test_selection_mode","numeric_aggregate_method","baseline_window_n","min_baseline_n","near_spec_margin_type","near_spec_margin_value"}
    for key in allowed:
        if key in payload: setattr(current,key,payload[key])
    for key,column in [("reference_fields","reference_fields_json"),("fallback_fields","fallback_fields_json"),("include_sample_types","include_sample_types_json"),("include_result_statuses","include_result_statuses_json"),("rules","rules_json"),("discrete","discrete_json")]:
        if key in payload: setattr(current,column,json.dumps(payload[key]))
    current.version+=1; current.updated_at=datetime.utcnow(); after=config_dict(current)
    db.add(AttentionConfigAudit(config_id=current.id,version=current.version,before_json=json.dumps(before,default=str),after_json=json.dumps(after,default=str),reason=payload.get("reason"),changed_by=payload.get("changed_by","SYSTEM")))
    db.commit(); return after

@router.get("/reference-profiler")
def reference_profiler(db:Session=Depends(get_db)):
    receipts=db.query(Receipt).all(); total=len(receipts); result=[]
    for field in REFERENCE_FIELDS:
        values=[str(getattr(x,field) or "").strip() for x in receipts]; populated=[x for x in values if x]; counts=defaultdict(int)
        for value in populated: counts[value]+=1
        result.append({"field":field,"total":total,"populated":len(populated),"populated_percent":round(100*len(populated)/total,1) if total else 0,"distinct":len(counts),"duplicate_records":sum(v-1 for v in counts.values() if v>1),"max_records_per_reference":max(counts.values(),default=0),"examples":list(counts)[:3]})
    return result

@router.post("/reference-profiler/preview")
def reference_preview(payload:dict=Body(...),db:Session=Depends(get_db)):
    fields=payload.get("fields") or ["supplier_batch_no"]; rows=db.query(Receipt).all(); counts=defaultdict(list); blank=0
    for receipt in rows:
        parts=[str(getattr(receipt,f) or "").strip() for f in fields]
        if not all(parts): blank+=1; continue
        counts[" | ".join(parts)].append(receipt)
    collisions=sum(1 for values in counts.values() if len({(x.supplier_id,x.material_id) for x in values})>1)
    return {"fields":fields,"records":len(rows),"distinct_references":len(counts),"blank_component_count":blank,"duplicate_records":sum(len(v)-1 for v in counts.values() if len(v)>1),"cross_supplier_material_collisions":collisions,"multi_receipt_references":sum(1 for v in counts.values() if len(v)>1)}

@router.post("/evaluate")
def run_evaluation(db:Session=Depends(get_db)):
    if not evaluation_lock.acquire(blocking=False):
        raise HTTPException(409,"An attention rule evaluation is already running")
    try:
        return evaluate(db)
    finally:
        evaluation_lock.release()

@router.get("/events")
def events(material_id:Optional[str]=None,supplier_id:Optional[str]=None,attribute_id:Optional[str]=None,severity:Optional[str]=None,status:Optional[str]=None,limit:int=Query(500,ge=1,le=5000),db:Session=Depends(get_db)):
    q=event_query(db)
    for column,value in [(AttentionEvent.material_id,material_id),(AttentionEvent.supplier_id,supplier_id),(AttentionEvent.attribute_id,attribute_id),(AttentionEvent.severity,severity),(AttentionEvent.status,status)]:
        if value: q=q.filter(column==value)
    return [event_dict(x) for x in q.order_by(AttentionEvent.event_time.desc()).limit(limit).all()]

@router.get("/events/{event_id}")
def event_detail(event_id:str,db:Session=Depends(get_db)):
    event=event_query(db).filter(AttentionEvent.id==event_id).first()
    if not event: raise HTTPException(404,"Attention event not found")
    return event_dict(event)

@router.post("/events/{event_id}/acknowledge")
def acknowledge(event_id:str,payload:dict=Body(default={}),db:Session=Depends(get_db)):
    event=db.get(AttentionEvent,event_id)
    if not event: raise HTTPException(404,"Attention event not found")
    event.status="ACKNOWLEDGED"; event.acknowledged_at=datetime.utcnow(); event.acknowledged_by=payload.get("acknowledged_by","SYSTEM"); db.commit()
    return {"id":event.id,"status":event.status,"acknowledged_at":event.acknowledged_at}

@router.get("/summary")
def summary(view:str=Query("material",pattern="^(material|supplier)$"),db:Session=Depends(get_db)):
    rows=[event_dict(x) for x in event_query(db).filter(AttentionEvent.status.in_(["OPEN","ACKNOWLEDGED"])).order_by(AttentionEvent.event_time.desc()).all()]; groups=defaultdict(list)
    for row in rows: groups[row["material_id"] if view=="material" else row["supplier_id"]].append(row)
    result=[]
    for values in groups.values():
        worst=max(values,key=lambda x:SEVERITY_RANK[x["severity"]])
        result.append({"id":worst[f"{view}_id"],"code":worst[f"{view}_code"],"name":worst[f"{view}_name"],"severity":worst["severity"],"open_events":sum(x["status"]=="OPEN" for x in values),"attributes":len({x["attribute_id"] for x in values}),"counterparties":len({x["supplier_id" if view=="material" else "material_id"] for x in values}),"latest_event":values[0]["event_time"],"reason":worst["message"],"events":values})
    return sorted(result,key=lambda x:(-SEVERITY_RANK[x["severity"]],str(x["name"])))

@router.get("/runs")
def runs(db:Session=Depends(get_db)): return db.query(AttentionRunLog).order_by(AttentionRunLog.started_at.desc()).limit(25).all()

@router.get("/reports/{report_code}")
def report(report_code:str,db:Session=Depends(get_db)):
    if report_code not in {"R01","R02","R03","R04","R05"}: raise HTTPException(404,"Unknown report")
    return {"report_code":report_code,"generated_at":datetime.utcnow(),"config":config_dict(get_config(db)),"rows":[event_dict(x) for x in event_query(db).order_by(AttentionEvent.event_time.desc()).all()]}
