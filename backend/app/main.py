from datetime import datetime
import re
import json
from collections import defaultdict
from decimal import Decimal
from statistics import mean, pstdev
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import IntegrityError
from .database import Base, engine, get_db, SessionLocal, ensure_schema_extensions
from .models import *
from .schemas import *
from .demo_data import clear_all_data, load_demo_data
from .attention.api import router as attention_router

Base.metadata.create_all(bind=engine)
ensure_schema_extensions()

app = FastAPI(title="FA-IQM API", version="0.1.0")
app.include_router(attention_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def next_no(db, model, prefix):
    n = db.query(model).count() + 1
    return f"{prefix}-{datetime.now():%Y%m%d}-{n:05d}"

def current_master_query(db, model, entity_type):
    archived = db.query(MasterResetArchive.entity_id).filter(MasterResetArchive.entity_type == entity_type)
    return db.query(model).filter(~model.id.in_(archived))

def restore_master(db, model, entity_type, code_column, code):
    row = db.query(model).filter(func.upper(code_column) == code).first()
    if not row:
        return None
    marker = db.query(MasterResetArchive).filter(
        MasterResetArchive.entity_type == entity_type,
        MasterResetArchive.entity_id == row.id,
    ).first()
    if not marker:
        raise HTTPException(409, f"{entity_type.replace('_', ' ').title()} code already exists")
    db.delete(marker)
    return row

def resolve_spec(db, material_id, supplier_id=None, transaction_at=None):
    """Resolve the specification that was effective at the material transaction time.
    The selected specification is persisted on the receipt and remains the validation
    basis for that batch even if the master specification later expires or changes.
    """
    at = transaction_at or datetime.utcnow()
    q = db.query(Specification).filter(
        Specification.material_id == material_id,
        Specification.status.in_(["APPROVED","APPROVED_HISTORY"]),
        Specification.created_at <= at,
        ~Specification.id.in_(db.query(MasterResetArchive.entity_id).filter(MasterResetArchive.entity_type == "specification")),
    )
    return q.order_by(Specification.created_at.desc()).first()

def next_spec_version(version: str):
    match=re.search(r"(\d+)(?!.*\d)",version)
    if not match: return f"{version}-1"
    number=str(int(match.group(1))+1).zfill(len(match.group(1)))
    return f"{version[:match.start()]}{number}{version[match.end():]}"

@app.get("/api/v1/health")
def health(): return {"status":"ok"}

@app.get("/api/v1/materials", response_model=list[MaterialOut])
def materials(db: Session=Depends(get_db)): return current_master_query(db, Material, "material").filter(Material.active==True).all()

@app.get("/api/v1/suppliers", response_model=list[SupplierOut])
def suppliers(db: Session=Depends(get_db)): return current_master_query(db, Supplier, "supplier").filter(Supplier.active==True).all()

# -------------------- Configuration masters --------------------
@app.get("/api/v1/config/plants")
def plants(db: Session=Depends(get_db)):
    return current_master_query(db, Plant, "plant").order_by(Plant.plant_code).all()

@app.post("/api/v1/config/plants")
def create_plant(data: PlantCreate, db: Session=Depends(get_db)):
    code=data.plant_code.strip().upper()
    row=restore_master(db, Plant, "plant", Plant.plant_code, code)
    if row:
        row.plant_name=data.plant_name.strip(); row.active=data.active
    else:
        row=Plant(plant_code=code,plant_name=data.plant_name.strip(),active=data.active); db.add(row)
    db.commit(); db.refresh(row); return row

@app.get("/api/v1/config/sms-locations")
def sms_locations(db: Session=Depends(get_db)):
    rows=current_master_query(db, SmsLocation, "sms_location").options(joinedload(SmsLocation.plant)).order_by(SmsLocation.sms_code).all()
    return [{"id":x.id,"plant_id":x.plant_id,"plant_code":x.plant.plant_code,"plant_name":x.plant.plant_name,
             "sms_code":x.sms_code,"sms_name":x.sms_name,"active":x.active} for x in rows]

@app.post("/api/v1/config/sms-locations")
def create_sms_location(data: SmsLocationCreate, db: Session=Depends(get_db)):
    if not db.get(Plant,data.plant_id): raise HTTPException(400,"Invalid plant")
    code=data.sms_code.strip().upper()
    row=db.query(SmsLocation).filter(SmsLocation.plant_id==data.plant_id,func.upper(SmsLocation.sms_code)==code).first()
    if row:
        marker=db.query(MasterResetArchive).filter_by(entity_type="sms_location",entity_id=row.id).first()
        if not marker: raise HTTPException(409,"SMS code already exists for this plant")
        db.delete(marker); row.sms_name=data.sms_name.strip(); row.active=data.active
    else:
        row=SmsLocation(plant_id=data.plant_id,sms_code=code,sms_name=data.sms_name.strip(),active=data.active); db.add(row)
    db.commit(); db.refresh(row); return row

@app.get("/api/v1/config/store-locations")
def store_locations(db: Session=Depends(get_db)):
    rows=current_master_query(db, StoreLocation, "store_location").options(joinedload(StoreLocation.sms).joinedload(SmsLocation.plant)).order_by(StoreLocation.store_code).all()
    return [{"id":x.id,"sms_id":x.sms_id,"sms_code":x.sms.sms_code,"sms_name":x.sms.sms_name,
             "plant_id":x.sms.plant_id,"plant_code":x.sms.plant.plant_code,"store_code":x.store_code,
             "store_name":x.store_name,"active":x.active} for x in rows]

@app.post("/api/v1/config/store-locations")
def create_store_location(data: StoreLocationCreate, db: Session=Depends(get_db)):
    if not db.get(SmsLocation,data.sms_id): raise HTTPException(400,"Invalid SMS location")
    code=data.store_code.strip().upper()
    row=db.query(StoreLocation).filter(StoreLocation.sms_id==data.sms_id,func.upper(StoreLocation.store_code)==code).first()
    if row:
        marker=db.query(MasterResetArchive).filter_by(entity_type="store_location",entity_id=row.id).first()
        if not marker: raise HTTPException(409,"Store code already exists for this SMS")
        db.delete(marker); row.store_name=data.store_name.strip(); row.active=data.active
    else:
        row=StoreLocation(sms_id=data.sms_id,store_code=code,store_name=data.store_name.strip(),active=data.active); db.add(row)
    db.commit(); db.refresh(row); return row

@app.get("/api/v1/config/attribute-groups")
def attribute_groups(db: Session=Depends(get_db)):
    return current_master_query(db, AttributeGroup, "attribute_group").order_by(AttributeGroup.group_name).all()

@app.post("/api/v1/config/attribute-groups")
def create_attribute_group(data: AttributeGroupCreate, db: Session=Depends(get_db)):
    code = data.group_code.strip().upper()
    group=restore_master(db, AttributeGroup, "attribute_group", AttributeGroup.group_code, code)
    if group:
        group.group_name=data.group_name.strip(); group.description=data.description; group.active=data.active
    else:
        group = AttributeGroup(**data.model_dump()); group.group_code = code; group.group_name = group.group_name.strip(); db.add(group)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409,"Attribute group code already exists")
    db.refresh(group); return group

@app.get("/api/v1/config/materials")
def config_materials(db: Session=Depends(get_db)):
    return current_master_query(db, Material, "material").order_by(Material.material_code).all()

@app.post("/api/v1/config/materials")
def create_material(data: MaterialCreate, db: Session=Depends(get_db)):
    code=data.material_code.strip().upper()
    m=restore_master(db, Material, "material", Material.material_code, code)
    if m:
        for key,value in data.model_dump().items(): setattr(m,key,value)
    else:
        m=Material(**data.model_dump()); db.add(m)
    m.material_code=code; m.material_name=m.material_name.strip(); m.material_description=m.material_description.strip()
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(409,"Material code already exists")
    db.refresh(m); return m

@app.get("/api/v1/config/suppliers")
def config_suppliers(db: Session=Depends(get_db)):
    return current_master_query(db, Supplier, "supplier").order_by(Supplier.supplier_code).all()

@app.post("/api/v1/config/suppliers")
def create_supplier(data: SupplierCreate, db: Session=Depends(get_db)):
    code=data.supplier_code.strip().upper()
    x=restore_master(db, Supplier, "supplier", Supplier.supplier_code, code)
    if x:
        x.supplier_name=data.supplier_name.strip(); x.active=data.active
    else:
        x=Supplier(**data.model_dump()); x.supplier_code=code; x.supplier_name=x.supplier_name.strip(); db.add(x)
    db.commit(); db.refresh(x); return x

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
    rows = current_master_query(db, QualityAttribute, "quality_attribute").options(joinedload(QualityAttribute.group)).order_by(QualityAttribute.attribute_code).all()
    return [{"id":x.id,"group_id":x.group_id,"group_code":x.group.group_code if x.group else None,
             "group_name":x.group.group_name if x.group else "Ungrouped","attribute_code":x.attribute_code,
             "attribute_name":x.attribute_name,"uom":x.uom,"data_type":x.data_type,
             "precision_scale":x.precision_scale,"test_method":x.test_method,
             "category_options":x.category_options.split("|") if x.category_options else [],"active":x.active} for x in rows]

@app.post("/api/v1/config/quality-attributes")
def create_quality_attribute(data: QualityAttributeCreate, db: Session=Depends(get_db)):
    if not db.get(AttributeGroup,data.group_id): raise HTTPException(400,"Invalid attribute group")
    payload=data.model_dump(exclude={"category_options"})
    code=data.attribute_code.strip().upper()
    x=restore_master(db, QualityAttribute, "quality_attribute", QualityAttribute.attribute_code, code)
    values={**payload,"category_options":"|".join(data.category_options) or None}
    if x:
        for key,value in values.items(): setattr(x,key,value)
    else:
        x=QualityAttribute(**values); db.add(x)
    x.attribute_code=code; x.attribute_name=x.attribute_name.strip(); db.commit(); db.refresh(x); return x

@app.get("/api/v1/config/specifications")
def specifications(db: Session=Depends(get_db)):
    rows=current_master_query(db, Specification, "specification").options(joinedload(Specification.material),joinedload(Specification.attributes).joinedload(SpecificationAttribute.attribute)).order_by(Specification.effective_from.desc()).all()
    now=datetime.utcnow()
    return [{"id":x.id,"material_id":x.material_id,"material_code":x.material.material_code,"material_name":x.material.material_name,"material_description":x.material.material_description,
             "version":x.version,"status":x.status,
             "effective_from":x.effective_from,"effective_to":x.effective_to,"created_at":x.created_at,"approved_at":x.approved_at,
             "is_current":x.status=="APPROVED" and resolve_spec(db,x.material_id,transaction_at=now) is not None and resolve_spec(db,x.material_id,transaction_at=now).id==x.id,
             "attributes":[{"id":a.id,"attribute_id":a.attribute_id,"code":a.attribute.attribute_code,"name":a.attribute.attribute_name,"data_type":a.attribute.data_type,"uom":a.attribute.uom,"mandatory":a.mandatory,"lsl":float(a.lsl) if a.lsl is not None else None,"aim_value":float(a.aim_value) if a.aim_value is not None else None,"usl":float(a.usl) if a.usl is not None else None,"target_value":a.target_value,"display_sequence":a.display_sequence} for a in sorted(x.attributes,key=lambda z:z.display_sequence)]} for x in rows]

@app.post("/api/v1/config/specifications")
def create_specification(data: SpecificationCreate, db: Session=Depends(get_db)):
    if not db.get(Material,data.material_id): raise HTTPException(400,"Invalid material")
    scope=current_master_query(db, Specification, "specification").filter(Specification.material_id==data.material_id)
    existing=scope.order_by(Specification.created_at).all()
    version=f"V{len(existing)+1}"
    now=datetime.utcnow()
    previous_current=existing[-1] if existing else None
    for previous in existing:
        if previous.status=="APPROVED": previous.status="APPROVED_HISTORY"
    sp=Specification(material_id=data.material_id,version=version,status="APPROVED",effective_from=now,effective_to=datetime(2099,12,31,23,59,59),created_at=now,approved_at=now)
    db.add(sp); db.flush()
    seen=set()
    for a in data.attributes:
        if a.attribute_id in seen: raise HTTPException(400,"Duplicate quality attribute in specification")
        seen.add(a.attribute_id)
        attribute = db.get(QualityAttribute,a.attribute_id)
        if not attribute: raise HTTPException(400,"Invalid quality attribute")
        if attribute.data_type == "NUMERIC" and a.aim_value is None:
            raise HTTPException(400,f"Aim value is required for numeric attribute {attribute.attribute_code}")
        db.add(SpecificationAttribute(specification_id=sp.id,**a.model_dump()))
    old_values={a.attribute_id:(a.mandatory,a.lsl,a.aim_value,a.usl,a.target_value) for a in previous_current.attributes} if previous_current else {}
    new_values={a.attribute_id:(a.mandatory,a.lsl,a.aim_value,a.usl,a.target_value) for a in sp.attributes}
    added=set(new_values)-set(old_values); removed=set(old_values)-set(new_values)
    modified={key for key in set(old_values)&set(new_values) if old_values[key]!=new_values[key]}
    summary={"added":len(added),"modified":len(modified),"removed":len(removed),"total_attributes":len(new_values)}
    db.add(SpecificationVersionLog(material_id=sp.material_id,
        previous_specification_id=previous_current.id if previous_current else None,new_specification_id=sp.id,
        previous_version=previous_current.version if previous_current else None,new_version=sp.version,
        change_summary=json.dumps(summary),changed_by="SYSTEM"))
    db.commit(); db.refresh(sp); return {"id":sp.id,"version":sp.version}

@app.get("/api/v1/config/specification-version-logs")
def specification_version_logs(db: Session=Depends(get_db)):
    rows=current_master_query(db, SpecificationVersionLog, "specification_version_log").options(joinedload(SpecificationVersionLog.material)).order_by(SpecificationVersionLog.changed_at.desc()).all()
    return [{"id":x.id,"material_code":x.material.material_code,"material_name":x.material.material_name,
        "previous_version":x.previous_version,
        "new_version":x.new_version,"change_summary":json.loads(x.change_summary),"changed_by":x.changed_by,"changed_at":x.changed_at} for x in rows]

@app.get("/api/v1/config/specifications/latest/{material_id}")
def latest_specification(material_id: str, db: Session=Depends(get_db)):
    if not db.get(Material,material_id): raise HTTPException(404,"Material not found")
    source=(current_master_query(db, Specification, "specification").options(joinedload(Specification.material),joinedload(Specification.attributes).joinedload(SpecificationAttribute.attribute))
            .filter(Specification.material_id==material_id,Specification.status.in_(["APPROVED","APPROVED_HISTORY"]))
            .order_by(Specification.approved_at.desc()).first())
    if not source: raise HTTPException(404,"No approved generic specification exists for this material")
    candidate=next_spec_version(source.version)
    existing={x.version.upper() for x in current_master_query(db, Specification, "specification").filter(Specification.material_id==material_id).all()}
    while candidate.upper() in existing: candidate=next_spec_version(candidate)
    return {"id":source.id,"material_code":source.material.material_code,"material_name":source.material.material_name,
            "version":source.version,"next_version":candidate,"effective_from":source.effective_from,"effective_to":source.effective_to,
            "attributes":[{"attribute_id":a.attribute_id,"group_id":a.attribute.group_id,"code":a.attribute.attribute_code,"name":a.attribute.attribute_name,"data_type":a.attribute.data_type,"uom":a.attribute.uom,
                           "lsl":float(a.lsl) if a.lsl is not None else None,"aim_value":float(a.aim_value) if a.aim_value is not None else None,
                           "usl":float(a.usl) if a.usl is not None else None,"target_value":a.target_value,"mandatory":a.mandatory}
                          for a in sorted(source.attributes,key=lambda x:x.display_sequence)]}

@app.post("/api/v1/config/specifications/{source_id}/new-version")
def create_new_specification_version(source_id: str, db: Session=Depends(get_db)):
    source=(current_master_query(db, Specification, "specification").options(joinedload(Specification.attributes)).filter(Specification.id==source_id).first())
    if not source or source.status not in {"APPROVED","APPROVED_HISTORY"}: raise HTTPException(400,"An approved specification is required as the source")
    candidate=next_spec_version(source.version)
    existing={x.version.upper() for x in current_master_query(db, Specification, "specification").filter(Specification.material_id==source.material_id).all()}
    while candidate.upper() in existing: candidate=next_spec_version(candidate)
    draft=Specification(material_id=source.material_id,version=candidate,status="DRAFT",effective_from=source.effective_from,effective_to=source.effective_to)
    db.add(draft); db.flush()
    for item in source.attributes:
        db.add(SpecificationAttribute(specification_id=draft.id,attribute_id=item.attribute_id,mandatory=item.mandatory,
            lsl=item.lsl,aim_value=item.aim_value,usl=item.usl,target_value=item.target_value,display_sequence=item.display_sequence))
    db.commit(); db.refresh(draft)
    return {"id":draft.id,"version":draft.version,"status":draft.status}

@app.post("/api/v1/config/specifications/{specification_id}/approve")
def approve_specification(specification_id: str, db: Session=Depends(get_db)):
    specification=db.get(Specification,specification_id)
    if not specification: raise HTTPException(404,"Specification not found")
    if specification.status=="APPROVED": raise HTTPException(409,"Specification is already approved")
    if specification.status!="DRAFT": raise HTTPException(409,"Only DRAFT specifications can be approved")
    others=db.query(Specification).filter(Specification.id!=specification.id,Specification.material_id==specification.material_id,
        Specification.effective_from==specification.effective_from,Specification.effective_to==specification.effective_to,
        Specification.status=="APPROVED")
    for previous in others.all(): previous.status="APPROVED_HISTORY"
    specification.status="APPROVED"; specification.approved_at=datetime.utcnow(); db.commit(); db.refresh(specification)
    return {"id":specification.id,"version":specification.version,"status":specification.status,"approved_at":specification.approved_at}

@app.post("/api/v1/config/reset-masters")
def reset_masters(db: Session=Depends(get_db)):
    """Archive current masters without deleting transaction dependencies."""
    entities = [
        ("store_location", StoreLocation), ("sms_location", SmsLocation), ("plant", Plant),
        ("specification_version_log", SpecificationVersionLog), ("specification", Specification),
        ("quality_attribute", QualityAttribute), ("attribute_group", AttributeGroup),
        ("supplier", Supplier), ("material", Material),
    ]
    reset_at = datetime.utcnow()
    counts = {}
    for entity_type, model in entities:
        rows = current_master_query(db, model, entity_type).all()
        counts[entity_type] = len(rows)
        db.add_all([MasterResetArchive(entity_type=entity_type, entity_id=row.id, reset_at=reset_at) for row in rows])
    db.commit()
    return {"message": "Master data reset completed. Transaction data was preserved.", "reset_at": reset_at, "archived": counts}

@app.post("/api/v1/config/reset-app")
def reset_app(db: Session=Depends(get_db)):
    counts = clear_all_data(db)
    return {"message": "Application reset completed. All master and transaction data was removed.", "deleted": counts}

@app.post("/api/v1/config/load-demo")
def load_demo(db: Session=Depends(get_db)):
    summary = load_demo_data(db, sample_count=50_100)
    return {"message": "Demo data loaded successfully.", **summary}


@app.get("/api/v1/receipts", response_model=list[ReceiptOut])
def receipts(limit: int = Query(500, ge=1, le=5000), db: Session=Depends(get_db)):
    return db.query(Receipt).options(joinedload(Receipt.material), joinedload(Receipt.supplier), joinedload(Receipt.specification)).order_by(Receipt.receipt_datetime.desc()).limit(limit).all()

@app.get("/api/v1/reports/material-quality-register")
def material_quality_register(db: Session=Depends(get_db)):
    rows=(db.query(Receipt).options(joinedload(Receipt.material),joinedload(Receipt.supplier),joinedload(Receipt.specification),joinedload(Receipt.plant),joinedload(Receipt.sms),joinedload(Receipt.store),joinedload(Receipt.samples).joinedload(Sample.results).joinedload(TestResult.specification_attribute).joinedload(SpecificationAttribute.attribute)).order_by(Receipt.receipt_datetime.desc()).all())
    result=[]
    for x in rows:
        exceptions=[]
        for sample in x.samples:
            for test in sample.results:
                if test.evaluation_status != "FAIL": continue
                specification_attribute=test.specification_attribute; attribute=specification_attribute.attribute
                observed=float(test.numeric_result) if test.numeric_result is not None else test.text_result
                exceptions.append({"attribute_code":attribute.attribute_code,"attribute_name":attribute.attribute_name,
                    "observed_value":observed,"uom":attribute.uom,"aim_value":float(specification_attribute.aim_value) if specification_attribute.aim_value is not None else specification_attribute.target_value,
                    "lsl":float(specification_attribute.lsl) if specification_attribute.lsl is not None else None,
                    "usl":float(specification_attribute.usl) if specification_attribute.usl is not None else None,
                    "sample_no":sample.sample_no})
        result.append({"id":x.id,"receipt_no":x.receipt_no,"receipt_datetime":x.receipt_datetime,
        "material_id":x.material_id,"material_code":x.material.material_code,"material_name":x.material.material_name,
        "supplier_id":x.supplier_id,"supplier_code":x.supplier.supplier_code,"supplier_name":x.supplier.supplier_name,
        "supplier_batch_no":x.supplier_batch_no,"internal_batch_no":x.internal_batch_no,"po_no":x.po_no,"grn_no":x.grn_no,
        "plant":x.plant.plant_name if x.plant else x.plant_code,"sms":x.sms.sms_name if x.sms else x.sms_code,
        "store":x.store.store_name if x.store else x.store_code,"specification_version":x.specification.version,
        "quantity":float(x.quantity),"uom":x.uom,"inspection_status":x.inspection_status,"release_state":x.release_state,
        "exceptions":exceptions})
    return result

ANALYSIS_REFERENCE_FIELDS = {
    "supplier_batch_no", "internal_batch_no", "receipt_no", "grn_no", "po_no",
    "vehicle_no", "plant_code", "sms_code", "store_code",
}

@app.get("/api/v1/analysis/batches")
def batch_analysis(
    reference_fields: str = "supplier_batch_no",
    consolidation: str = "ALL",
    supplier_id: str | None = None,
    material_id: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    fields = [field.strip() for field in reference_fields.split(",") if field.strip()]
    if not fields or any(field not in ANALYSIS_REFERENCE_FIELDS for field in fields):
        raise HTTPException(400, "Select at least one valid reference field")
    policy = consolidation.strip().upper()
    if policy not in {"ALL", "LATEST", "MEAN"}:
        raise HTTPException(400, "Consolidation must be ALL, LATEST, or MEAN")

    query = db.query(Receipt).options(joinedload(Receipt.material), joinedload(Receipt.supplier), joinedload(Receipt.specification))
    if supplier_id: query = query.filter(Receipt.supplier_id == supplier_id)
    if material_id: query = query.filter(Receipt.material_id == material_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(
            Receipt.receipt_no.ilike(term), Receipt.supplier_batch_no.ilike(term),
            Receipt.internal_batch_no.ilike(term), Receipt.po_no.ilike(term),
            Receipt.grn_no.ilike(term), Receipt.vehicle_no.ilike(term),
        ))
    receipts = query.order_by(Receipt.receipt_datetime).all()

    grouped_receipts = defaultdict(list)
    receipt_reference = {}
    for receipt in receipts:
        values = [str(getattr(receipt, field, None) or "").strip() for field in fields]
        reference_id = " | ".join(values) if all(values) else f"Receipt {receipt.receipt_no}"
        grouped_receipts[reference_id].append(receipt)
        receipt_reference[receipt.id] = reference_id

    receipt_ids = [receipt.id for receipt in receipts]
    results = []
    if receipt_ids:
        results = (db.query(TestResult)
            .options(joinedload(TestResult.specification_attribute).joinedload(SpecificationAttribute.attribute), joinedload(TestResult.sample))
            .join(Sample, TestResult.sample_id == Sample.id)
            .filter(Sample.receipt_id.in_(receipt_ids), TestResult.numeric_result.isnot(None))
            .all())

    observations = defaultdict(lambda: defaultdict(list))
    attribute_meta = {}
    receipt_by_id = {receipt.id: receipt for receipt in receipts}
    for result in results:
        receipt = receipt_by_id[result.sample.receipt_id]
        reference_id = receipt_reference[receipt.id]
        spec_attribute = result.specification_attribute
        attribute = spec_attribute.attribute
        attribute_meta[attribute.id] = {
            "attribute_id": attribute.id, "code": attribute.attribute_code,
            "name": attribute.attribute_name, "uom": attribute.uom,
        }
        observations[reference_id][attribute.id].append({
            "receipt_id": receipt.id, "receipt_no": receipt.receipt_no,
            "sample_no": result.sample.sample_no, "date": result.entered_at or receipt.receipt_datetime,
            "value": float(result.numeric_result),
            "lsl": float(spec_attribute.lsl) if spec_attribute.lsl is not None else None,
            "aim": float(spec_attribute.aim_value) if spec_attribute.aim_value is not None else None,
            "usl": float(spec_attribute.usl) if spec_attribute.usl is not None else None,
            "status": result.evaluation_status,
        })

    series = {attribute_id: {**meta, "points": []} for attribute_id, meta in attribute_meta.items()}
    for reference_id, attributes in observations.items():
        for attribute_id, points in attributes.items():
            points.sort(key=lambda point: point["date"])
            if policy == "LATEST":
                selected = [{**points[-1], "source_count": len(points)}]
            elif policy == "MEAN":
                latest = points[-1]
                selected = [{**latest, "value": mean(point["value"] for point in points), "receipt_no": f"Mean of {len(points)}", "sample_no": "—", "source_count": len(points)}]
            else:
                selected = [{**point, "source_count": 1} for point in points]
            for point in selected:
                series[attribute_id]["points"].append({**point, "reference_id": reference_id})

    for item in series.values():
        item["points"].sort(key=lambda point: point["date"])
        values = [point["value"] for point in item["points"]]
        center = mean(values) if values else None
        sigma = pstdev(values) if len(values) > 1 else 0
        latest_point = item["points"][-1] if item["points"] else {}
        lsl, usl = latest_point.get("lsl"), latest_point.get("usl")
        capability = None
        if sigma and center is not None:
            distances = []
            if usl is not None: distances.append((usl - center) / (3 * sigma))
            if lsl is not None: distances.append((center - lsl) / (3 * sigma))
            if distances: capability = min(distances)
        item["stats"] = {
            "count": len(values), "mean": center, "sigma": sigma,
            "minimum": min(values) if values else None, "maximum": max(values) if values else None,
            "lcl": center - 3 * sigma if center is not None else None,
            "ucl": center + 3 * sigma if center is not None else None,
            "cpk": capability,
        }

    batches = []
    for reference_id, group in grouped_receipts.items():
        latest = max(group, key=lambda receipt: receipt.receipt_datetime)
        batches.append({
            "reference_id": reference_id, "receipt_count": len(group),
            "latest_receipt_id": latest.id, "latest_receipt_no": latest.receipt_no,
            "receipt_datetime": latest.receipt_datetime,
            "supplier_id": latest.supplier_id, "supplier_code": latest.supplier.supplier_code,
            "supplier_name": latest.supplier.supplier_name,
            "material_id": latest.material_id, "material_code": latest.material.material_code,
            "material_name": latest.material.material_name,
            "supplier_batch_no": latest.supplier_batch_no, "internal_batch_no": latest.internal_batch_no,
            "po_no": latest.po_no, "grn_no": latest.grn_no, "vehicle_no": latest.vehicle_no,
            "status": latest.inspection_status, "specification_version": latest.specification.version,
            "numeric_attributes": len(observations.get(reference_id, {})),
        })
    batches.sort(key=lambda item: item["receipt_datetime"], reverse=True)
    return {"reference_fields": fields, "consolidation": policy, "batches": batches, "series": list(series.values())}

@app.post("/api/v1/receipts", response_model=ReceiptOut)
def create_receipt(data: ReceiptCreate, db: Session=Depends(get_db)):
    plant=db.get(Plant,data.plant_id); sms=db.get(SmsLocation,data.sms_id); store=db.get(StoreLocation,data.store_id)
    if not plant or not plant.active: raise HTTPException(400,"Invalid or inactive plant")
    if not sms or not sms.active or sms.plant_id!=plant.id: raise HTTPException(400,"SMS location does not belong to the selected plant")
    if not store or not store.active or store.sms_id!=sms.id: raise HTTPException(400,"Store location does not belong to the selected SMS")
    transaction_at=data.receipt_datetime or datetime.utcnow()
    spec=resolve_spec(db,data.material_id,data.supplier_id,transaction_at)
    if not spec: raise HTTPException(400,f"No quality specification version existed on {transaction_at:%Y-%m-%d %H:%M} for this material.")
    payload=data.model_dump(exclude={"receipt_datetime"})
    r=Receipt(receipt_no=next_no(db,Receipt,"FA-RCV"), specification_id=spec.id, receipt_datetime=transaction_at,
              plant_code=plant.plant_code,sms_code=sms.sms_code,store_code=store.store_code,**payload)
    db.add(r); db.commit(); db.refresh(r)
    return db.query(Receipt).options(joinedload(Receipt.material),joinedload(Receipt.supplier)).get(r.id)

@app.get("/api/v1/receipts/{rid}")
def receipt_detail(rid: str, db: Session=Depends(get_db)):
    r=db.query(Receipt).options(joinedload(Receipt.material),joinedload(Receipt.supplier),joinedload(Receipt.specification).joinedload(Specification.attributes).joinedload(SpecificationAttribute.attribute),joinedload(Receipt.samples)).filter(Receipt.id==rid).first()
    if not r: raise HTTPException(404,"Receipt not found")
    return {
      "id":r.id,"receipt_no":r.receipt_no,"status":r.inspection_status,"release_state":r.release_state,
      "material":{"code":r.material.material_code,"name":r.material.material_name,"description":r.material.material_description},
      "supplier":{"code":r.supplier.supplier_code,"name":r.supplier.supplier_name},
      "supplier_batch_no":r.supplier_batch_no,"internal_batch_no":r.internal_batch_no,"po_no":r.po_no,"grn_no":r.grn_no,
      "location":{"plant_code":r.plant_code,"plant_name":r.plant.plant_name if r.plant else None,"sms_code":r.sms_code,"sms_name":r.sms.sms_name if r.sms else None,"store_code":r.store_code,"store_name":r.store.store_name if r.store else None},
      "quantity":float(r.quantity),"uom":r.uom,"receipt_datetime":r.receipt_datetime,"specification":{"id":r.specification.id,"version":r.specification.version,"effective_from":r.specification.effective_from,"effective_to":r.specification.effective_to,
      "attributes":[{"id":x.id,"code":x.attribute.attribute_code,"name":x.attribute.attribute_name,"data_type":x.attribute.data_type,"uom":x.attribute.uom,"lsl":float(x.lsl) if x.lsl is not None else None,"aim_value":float(x.aim_value) if x.aim_value is not None else None,"usl":float(x.usl) if x.usl is not None else None,"target_value":x.target_value} for x in sorted(r.specification.attributes,key=lambda z:z.display_sequence)]},
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
             "data_type":a.attribute.data_type,"category_options":a.attribute.category_options.split("|") if a.attribute.category_options else [],"target_value":a.target_value,
             "lsl":float(a.lsl) if a.lsl is not None else None,"aim_value":float(a.aim_value) if a.aim_value is not None else None,"usl":float(a.usl) if a.usl is not None else None,
             "result":(float(existing[a.id].numeric_result) if existing[a.id].numeric_result is not None else existing[a.id].text_result) if a.id in existing else None,
             "evaluation":existing[a.id].evaluation_status if a.id in existing else "PENDING"} for a in attrs]

@app.put("/api/v1/samples/{sid}/results")
def save_results(sid:str,items:list[ResultIn],db:Session=Depends(get_db)):
    s=db.get(Sample,sid)
    if not s: raise HTTPException(404,"Sample not found")
    if s.sample_status != "TESTING":
        raise HTTPException(409,"Quality results are locked after submission and cannot be edited")
    for item in items:
        sa=db.get(SpecificationAttribute,item.specification_attribute_id)
        if not sa: raise HTTPException(400,"Invalid specification attribute")
        tr=db.query(TestResult).filter_by(sample_id=sid,specification_attribute_id=sa.id).first()
        if not tr:
            tr=TestResult(sample_id=sid,specification_attribute_id=sa.id); db.add(tr)
        tr.numeric_result=item.numeric_result; tr.text_result=item.text_result
        if sa.attribute.data_type=="NUMERIC" and item.numeric_result is not None:
            val=Decimal(item.numeric_result)
            tr.evaluation_status="PASS" if (sa.lsl is None or val>=sa.lsl) and (sa.usl is None or val<=sa.usl) else "FAIL"
        elif sa.attribute.data_type!="NUMERIC" and item.text_result:
            tr.evaluation_status="PASS" if not sa.target_value or item.text_result==sa.target_value else "FAIL"
        else: tr.evaluation_status="PENDING"
    db.commit()
    return required_tests(sid,db)

@app.post("/api/v1/samples/{sid}/results/submit")
def submit_results(sid:str,db:Session=Depends(get_db)):
    s=db.get(Sample,sid); 
    if not s: raise HTTPException(404,"Sample not found")
    if s.sample_status != "TESTING":
        raise HTTPException(409,"Only results currently under testing can be submitted")
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
    allowed={"ACCEPTED","ACCEPTED_WITH_DEVIATION","CONDITIONALLY_ACCEPTED","ON_HOLD","REJECTED"}
    if data.disposition not in allowed: raise HTTPException(400,"Unsupported disposition")
    results=db.query(TestResult).join(Sample,TestResult.sample_id==Sample.id).filter(Sample.receipt_id==rid,TestResult.result_status=="APPROVED").all()
    has_fail=any(x.evaluation_status=="FAIL" for x in results)
    if data.disposition=="ACCEPTED" and has_fail: raise HTTPException(409,"Failed mandatory results prevent normal acceptance")
    if data.disposition in {"ACCEPTED_WITH_DEVIATION","CONDITIONALLY_ACCEPTED","ON_HOLD","REJECTED"} and not data.reason_text:
        raise HTTPException(400,"Reason is required")
    db.add(Disposition(receipt_id=rid,disposition=data.disposition,reason_text=data.reason_text))
    r.inspection_status=data.disposition
    r.release_state="RELEASED" if data.disposition in {"ACCEPTED","ACCEPTED_WITH_DEVIATION","CONDITIONALLY_ACCEPTED"} else ("REJECTED" if data.disposition=="REJECTED" else "BLOCKED")
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
