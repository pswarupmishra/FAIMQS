from datetime import datetime
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from .database import Base, engine, get_db, SessionLocal
from .models import *
from .schemas import *
from .seed import seed

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed(db)

app = FastAPI(title="FA-IQM API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def next_no(db, model, prefix):
    n = db.query(model).count() + 1
    return f"{prefix}-{datetime.now():%Y%m%d}-{n:05d}"

def resolve_spec(db, material_id, supplier_id, transaction_at=None):
    """Resolve the specification that was effective at the material transaction time.
    The selected specification is persisted on the receipt and remains the validation
    basis for that batch even if the master specification later expires or changes.
    """
    at = transaction_at or datetime.utcnow()
    q = db.query(Specification).filter(
        Specification.material_id == material_id,
        Specification.status == "APPROVED",
        Specification.effective_from <= at,
        Specification.effective_to >= at
    )
    return (q.filter(Specification.supplier_id == supplier_id)
              .order_by(Specification.effective_from.desc()).first()
            or q.filter(Specification.supplier_id == None)
              .order_by(Specification.effective_from.desc()).first())

@app.get("/api/v1/health")
def health(): return {"status":"ok"}

@app.get("/api/v1/materials", response_model=list[MaterialOut])
def materials(db: Session=Depends(get_db)): return db.query(Material).filter(Material.active==True).all()

@app.get("/api/v1/suppliers", response_model=list[SupplierOut])
def suppliers(db: Session=Depends(get_db)): return db.query(Supplier).filter(Supplier.active==True).all()

# -------------------- Configuration masters --------------------
@app.get("/api/v1/config/materials")
def config_materials(db: Session=Depends(get_db)):
    return db.query(Material).order_by(Material.material_code).all()

@app.post("/api/v1/config/materials")
def create_material(data: MaterialCreate, db: Session=Depends(get_db)):
    if db.query(Material).filter(func.upper(Material.material_code)==data.material_code.strip().upper()).first():
        raise HTTPException(409,"Material code already exists")
    m=Material(**data.model_dump())
    m.material_code=m.material_code.strip().upper(); m.material_description=m.material_description.strip()
    db.add(m); db.commit(); db.refresh(m); return m

@app.get("/api/v1/config/suppliers")
def config_suppliers(db: Session=Depends(get_db)):
    return db.query(Supplier).order_by(Supplier.supplier_code).all()

@app.post("/api/v1/config/suppliers")
def create_supplier(data: SupplierCreate, db: Session=Depends(get_db)):
    if db.query(Supplier).filter(func.upper(Supplier.supplier_code)==data.supplier_code.strip().upper()).first():
        raise HTTPException(409,"Supplier code already exists")
    x=Supplier(**data.model_dump()); x.supplier_code=x.supplier_code.strip().upper(); x.supplier_name=x.supplier_name.strip()
    db.add(x); db.commit(); db.refresh(x); return x

@app.patch("/api/v1/config/suppliers/{supplier_id}/status")
def update_supplier_status(supplier_id: str, data: SupplierStatusUpdate, db: Session=Depends(get_db)):
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "Supplier not found")
    supplier.active = data.active
    db.commit(); db.refresh(supplier)
    return supplier

@app.get("/api/v1/config/quality-attributes")
def quality_attributes(db: Session=Depends(get_db)):
    return db.query(QualityAttribute).order_by(QualityAttribute.attribute_code).all()

@app.post("/api/v1/config/quality-attributes")
def create_quality_attribute(data: QualityAttributeCreate, db: Session=Depends(get_db)):
    if db.query(QualityAttribute).filter(func.upper(QualityAttribute.attribute_code)==data.attribute_code.strip().upper()).first():
        raise HTTPException(409,"Quality attribute code already exists")
    x=QualityAttribute(**data.model_dump()); x.attribute_code=x.attribute_code.strip().upper(); x.attribute_name=x.attribute_name.strip()
    db.add(x); db.commit(); db.refresh(x); return x

@app.get("/api/v1/config/specifications")
def specifications(db: Session=Depends(get_db)):
    rows=db.query(Specification).options(joinedload(Specification.material),joinedload(Specification.supplier),joinedload(Specification.attributes).joinedload(SpecificationAttribute.attribute)).order_by(Specification.effective_from.desc()).all()
    return [{"id":x.id,"material_id":x.material_id,"material_code":x.material.material_code,"material_description":x.material.material_description,
             "supplier_id":x.supplier_id,"supplier":x.supplier.supplier_name if x.supplier else "All suppliers (generic)","version":x.version,"status":x.status,
             "effective_from":x.effective_from,"effective_to":x.effective_to,
             "attributes":[{"id":a.id,"attribute_id":a.attribute_id,"code":a.attribute.attribute_code,"name":a.attribute.attribute_name,"uom":a.attribute.uom,"mandatory":a.mandatory,"lsl":float(a.lsl) if a.lsl is not None else None,"usl":float(a.usl) if a.usl is not None else None,"display_sequence":a.display_sequence} for a in sorted(x.attributes,key=lambda z:z.display_sequence)]} for x in rows]

@app.post("/api/v1/config/specifications")
def create_specification(data: SpecificationCreate, db: Session=Depends(get_db)):
    if not db.get(Material,data.material_id): raise HTTPException(400,"Invalid material")
    if data.supplier_id and not db.get(Supplier,data.supplier_id): raise HTTPException(400,"Invalid supplier")
    # Prevent ambiguous validity: date ranges may not overlap for the same material + supplier scope.
    overlap=db.query(Specification).filter(
        Specification.material_id==data.material_id,
        Specification.status=="APPROVED",
        Specification.effective_from <= data.effective_to,
        Specification.effective_to >= data.effective_from
    )
    overlap=overlap.filter(Specification.supplier_id==data.supplier_id) if data.supplier_id else overlap.filter(Specification.supplier_id==None)
    if data.status=="APPROVED" and overlap.first():
        raise HTTPException(409,"Specification validity overlaps an existing approved specification for the same material/supplier scope")
    sp=Specification(material_id=data.material_id,supplier_id=data.supplier_id,version=data.version.strip(),status=data.status,effective_from=data.effective_from,effective_to=data.effective_to)
    db.add(sp); db.flush()
    seen=set()
    for a in data.attributes:
        if a.attribute_id in seen: raise HTTPException(400,"Duplicate quality attribute in specification")
        seen.add(a.attribute_id)
        if not db.get(QualityAttribute,a.attribute_id): raise HTTPException(400,"Invalid quality attribute")
        db.add(SpecificationAttribute(specification_id=sp.id,**a.model_dump()))
    db.commit(); db.refresh(sp); return {"id":sp.id,"version":sp.version}


@app.get("/api/v1/receipts", response_model=list[ReceiptOut])
def receipts(db: Session=Depends(get_db)):
    return db.query(Receipt).options(joinedload(Receipt.material), joinedload(Receipt.supplier)).order_by(Receipt.receipt_datetime.desc()).all()

@app.post("/api/v1/receipts", response_model=ReceiptOut)
def create_receipt(data: ReceiptCreate, db: Session=Depends(get_db)):
    transaction_at=data.receipt_datetime or datetime.utcnow()
    spec=resolve_spec(db,data.material_id,data.supplier_id,transaction_at)
    if not spec: raise HTTPException(400,f"No approved quality specification is effective on {transaction_at:%Y-%m-%d %H:%M} for this material/supplier.")
    payload=data.model_dump(exclude={"receipt_datetime"})
    r=Receipt(receipt_no=next_no(db,Receipt,"FA-RCV"), specification_id=spec.id, receipt_datetime=transaction_at, **payload)
    db.add(r); db.commit(); db.refresh(r)
    return db.query(Receipt).options(joinedload(Receipt.material),joinedload(Receipt.supplier)).get(r.id)

@app.get("/api/v1/receipts/{rid}")
def receipt_detail(rid: str, db: Session=Depends(get_db)):
    r=db.query(Receipt).options(joinedload(Receipt.material),joinedload(Receipt.supplier),joinedload(Receipt.specification).joinedload(Specification.attributes).joinedload(SpecificationAttribute.attribute),joinedload(Receipt.samples)).filter(Receipt.id==rid).first()
    if not r: raise HTTPException(404,"Receipt not found")
    return {
      "id":r.id,"receipt_no":r.receipt_no,"status":r.inspection_status,"release_state":r.release_state,
      "material":{"code":r.material.material_code,"description":r.material.material_description},
      "supplier":{"code":r.supplier.supplier_code,"name":r.supplier.supplier_name},
      "supplier_batch_no":r.supplier_batch_no,"internal_batch_no":r.internal_batch_no,"po_no":r.po_no,
      "quantity":float(r.quantity),"uom":r.uom,"receipt_datetime":r.receipt_datetime,"specification":{"id":r.specification.id,"version":r.specification.version,"effective_from":r.specification.effective_from,"effective_to":r.specification.effective_to,
      "attributes":[{"id":x.id,"code":x.attribute.attribute_code,"name":x.attribute.attribute_name,"uom":x.attribute.uom,"lsl":float(x.lsl) if x.lsl is not None else None,"usl":float(x.usl) if x.usl is not None else None} for x in sorted(r.specification.attributes,key=lambda z:z.display_sequence)]},
      "samples":[{"id":s.id,"sample_no":s.sample_no,"sample_type":s.sample_type,"sample_status":s.sample_status} for s in r.samples]
    }

@app.post("/api/v1/receipts/{rid}/submit")
def submit_receipt(rid:str, db:Session=Depends(get_db)):
    r=db.get(Receipt,rid)
    if not r: raise HTTPException(404,"Receipt not found")
    if r.inspection_status!="DRAFT": raise HTTPException(409,"Only DRAFT receipt can be submitted")
    r.inspection_status="PENDING_SAMPLING"; db.commit()
    return {"status":r.inspection_status,"release_state":r.release_state}

@app.post("/api/v1/receipts/{rid}/samples")
def create_sample(rid:str,data:SampleCreate,db:Session=Depends(get_db)):
    r=db.get(Receipt,rid)
    if not r: raise HTTPException(404,"Receipt not found")
    s=Sample(sample_no=next_no(db,Sample,f"FA-{r.plant_code}"),receipt_id=rid,**data.model_dump())
    db.add(s); r.inspection_status="SAMPLING_IN_PROGRESS"; db.commit(); db.refresh(s)
    return {"id":s.id,"sample_no":s.sample_no,"sample_status":s.sample_status}

@app.post("/api/v1/samples/{sid}/{action}")
def sample_action(sid:str,action:str,db:Session=Depends(get_db)):
    s=db.get(Sample,sid)
    if not s: raise HTTPException(404,"Sample not found")
    transitions={
      ("CREATED","collect"):"COLLECTED",("COLLECTED","send-to-lab"):"SENT_TO_LAB",
      ("SENT_TO_LAB","receive-at-lab"):"RECEIVED_AT_LAB",("RECEIVED_AT_LAB","start-testing"):"TESTING"
    }
    nxt=transitions.get((s.sample_status,action))
    if not nxt: raise HTTPException(409,f"Invalid sample transition {s.sample_status} -> {action}")
    s.sample_status=nxt
    r=db.get(Receipt,s.receipt_id)
    r.inspection_status={"COLLECTED":"SAMPLING_IN_PROGRESS","SENT_TO_LAB":"SAMPLE_SENT_TO_LAB","RECEIVED_AT_LAB":"LAB_IN_PROGRESS","TESTING":"LAB_IN_PROGRESS"}[nxt]
    db.commit()
    return {"sample_status":nxt,"receipt_status":r.inspection_status}

@app.get("/api/v1/samples/{sid}/required-tests")
def required_tests(sid:str,db:Session=Depends(get_db)):
    s=db.get(Sample,sid)
    if not s: raise HTTPException(404,"Sample not found")
    r=db.get(Receipt,s.receipt_id)
    attrs=db.query(SpecificationAttribute).options(joinedload(SpecificationAttribute.attribute)).filter(SpecificationAttribute.specification_id==r.specification_id).order_by(SpecificationAttribute.display_sequence).all()
    existing={x.specification_attribute_id:x for x in db.query(TestResult).filter(TestResult.sample_id==sid).all()}
    return [{"specification_attribute_id":a.id,"code":a.attribute.attribute_code,"name":a.attribute.attribute_name,"uom":a.attribute.uom,
             "lsl":float(a.lsl) if a.lsl is not None else None,"usl":float(a.usl) if a.usl is not None else None,
             "result":float(existing[a.id].numeric_result) if a.id in existing and existing[a.id].numeric_result is not None else None,
             "evaluation":existing[a.id].evaluation_status if a.id in existing else "PENDING"} for a in attrs]

@app.put("/api/v1/samples/{sid}/results")
def save_results(sid:str,items:list[ResultIn],db:Session=Depends(get_db)):
    s=db.get(Sample,sid)
    if not s: raise HTTPException(404,"Sample not found")
    for item in items:
        sa=db.get(SpecificationAttribute,item.specification_attribute_id)
        if not sa: raise HTTPException(400,"Invalid specification attribute")
        tr=db.query(TestResult).filter_by(sample_id=sid,specification_attribute_id=sa.id).first()
        if not tr:
            tr=TestResult(sample_id=sid,specification_attribute_id=sa.id); db.add(tr)
        tr.numeric_result=item.numeric_result; tr.text_result=item.text_result
        if item.numeric_result is None: tr.evaluation_status="PENDING"
        else:
            val=Decimal(item.numeric_result)
            tr.evaluation_status="PASS" if (sa.lsl is None or val>=sa.lsl) and (sa.usl is None or val<=sa.usl) else "FAIL"
    db.commit()
    return required_tests(sid,db)

@app.post("/api/v1/samples/{sid}/results/submit")
def submit_results(sid:str,db:Session=Depends(get_db)):
    s=db.get(Sample,sid); 
    if not s: raise HTTPException(404,"Sample not found")
    r=db.get(Receipt,s.receipt_id)
    attrs=db.query(SpecificationAttribute).filter_by(specification_id=r.specification_id,mandatory=True).all()
    results={x.specification_attribute_id:x for x in db.query(TestResult).filter_by(sample_id=sid).all()}
    missing=[a.id for a in attrs if a.id not in results or results[a.id].evaluation_status=="PENDING"]
    if missing: raise HTTPException(400,"All mandatory test results are required")
    for x in results.values(): x.result_status="SUBMITTED"
    s.sample_status="RESULTS_SUBMITTED"; r.inspection_status="RESULTS_AVAILABLE"; db.commit()
    return {"sample_status":s.sample_status,"receipt_status":r.inspection_status}

@app.post("/api/v1/samples/{sid}/results/approve")
def approve_results(sid:str,db:Session=Depends(get_db)):
    s=db.get(Sample,sid)
    if not s or s.sample_status!="RESULTS_SUBMITTED": raise HTTPException(409,"Results must be submitted first")
    for x in db.query(TestResult).filter_by(sample_id=sid).all(): x.result_status="APPROVED"
    s.sample_status="RESULTS_APPROVED"
    r=db.get(Receipt,s.receipt_id); r.inspection_status="UNDER_REVIEW"; db.commit()
    return {"sample_status":s.sample_status,"receipt_status":r.inspection_status}

@app.post("/api/v1/receipts/{rid}/disposition")
def disposition(rid:str,data:DispositionIn,db:Session=Depends(get_db)):
    r=db.get(Receipt,rid)
    if not r: raise HTTPException(404,"Receipt not found")
    allowed={"ACCEPTED","CONDITIONALLY_ACCEPTED","ON_HOLD","REJECTED"}
    if data.disposition not in allowed: raise HTTPException(400,"Unsupported disposition")
    results=db.query(TestResult).join(Sample,TestResult.sample_id==Sample.id).filter(Sample.receipt_id==rid,TestResult.result_status=="APPROVED").all()
    has_fail=any(x.evaluation_status=="FAIL" for x in results)
    if data.disposition=="ACCEPTED" and has_fail: raise HTTPException(409,"Failed mandatory results prevent normal acceptance")
    if data.disposition in {"CONDITIONALLY_ACCEPTED","ON_HOLD","REJECTED"} and not data.reason_text:
        raise HTTPException(400,"Reason is required")
    db.add(Disposition(receipt_id=rid,disposition=data.disposition,reason_text=data.reason_text))
    r.inspection_status=data.disposition
    r.release_state="RELEASED" if data.disposition in {"ACCEPTED","CONDITIONALLY_ACCEPTED"} else ("REJECTED" if data.disposition=="REJECTED" else "BLOCKED")
    db.commit()
    return {"inspection_status":r.inspection_status,"release_state":r.release_state}

@app.get("/api/v1/dashboard")
def dashboard(db:Session=Depends(get_db)):
    total=db.query(Receipt).count()
    return {
      "total":total,
      "pending_sampling":db.query(Receipt).filter(Receipt.inspection_status.in_(["PENDING_SAMPLING","SAMPLING_IN_PROGRESS"])).count(),
      "lab_pending":db.query(Receipt).filter(Receipt.inspection_status.in_(["SAMPLE_SENT_TO_LAB","LAB_IN_PROGRESS","RESULTS_AVAILABLE"])).count(),
      "under_review":db.query(Receipt).filter(Receipt.inspection_status=="UNDER_REVIEW").count(),
      "on_hold":db.query(Receipt).filter(Receipt.inspection_status=="ON_HOLD").count(),
      "released":db.query(Receipt).filter(Receipt.release_state=="RELEASED").count(),
      "rejected":db.query(Receipt).filter(Receipt.release_state=="REJECTED").count(),
    }
