from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from .models import AttributeGroup, Material, Plant, SmsLocation, StoreLocation, Supplier, QualityAttribute, Specification, SpecificationAttribute

def seed(db: Session):
    plant = db.query(Plant).filter_by(plant_code="VJNR").first()
    if not plant:
        plant = Plant(plant_code="VJNR", plant_name="Vijayanagar Plant")
        db.add(plant); db.flush()
    sms = db.query(SmsLocation).filter_by(plant_id=plant.id, sms_code="SMS1").first()
    if not sms:
        sms = SmsLocation(plant_id=plant.id, sms_code="SMS1", sms_name="Steel Melting Shop 1")
        db.add(sms); db.flush()
    store = db.query(StoreLocation).filter_by(sms_id=sms.id, store_code="FA_STORE").first()
    if not store:
        db.add(StoreLocation(sms_id=sms.id, store_code="FA_STORE", store_name="Ferro Alloy Store"))
    chemistry = db.query(AttributeGroup).filter_by(group_code="CHEMISTRY").first()
    if not chemistry:
        chemistry = AttributeGroup(group_code="CHEMISTRY", group_name="Chemistry", description="Chemical composition attributes")
        db.add(chemistry); db.flush()
    db.query(QualityAttribute).filter(QualityAttribute.group_id==None).update({QualityAttribute.group_id:chemistry.id})
    if db.query(Material).count():
        db.commit()
        return
    mats = [
        Material(material_code="FA000123", material_name="Ferro Silicon", material_description="Ferro Silicon"),
        Material(material_code="FA000124", material_name="Ferro Manganese", material_description="Ferro Manganese"),
        Material(material_code="FA000125", material_name="Silico Manganese", material_description="Silico Manganese"),
        Material(material_code="FA000126", material_name="Ferro Chrome", material_description="Ferro Chrome"),
        Material(material_code="FA000127", material_name="Ferro Vanadium", material_description="Ferro Vanadium"),
    ]
    sups = [
        Supplier(supplier_code="SUP001", supplier_name="Demo Alloy Supplier A"),
        Supplier(supplier_code="SUP002", supplier_name="Demo Alloy Supplier B"),
        Supplier(supplier_code="SUP003", supplier_name="Demo Metals Supplier C"),
        Supplier(supplier_code="SUP004", supplier_name="Demo Minerals Supplier D"),
    ]
    attrs = [
        QualityAttribute(group_id=chemistry.id, attribute_code="SI", attribute_name="Silicon", uom="%"),
        QualityAttribute(group_id=chemistry.id, attribute_code="MN", attribute_name="Manganese", uom="%"),
        QualityAttribute(group_id=chemistry.id, attribute_code="C", attribute_name="Carbon", uom="%"),
        QualityAttribute(group_id=chemistry.id, attribute_code="P", attribute_name="Phosphorus", uom="%"),
        QualityAttribute(group_id=chemistry.id, attribute_code="S", attribute_name="Sulphur", uom="%"),
    ]
    db.add_all(mats+sups+attrs); db.flush()
    # DEMO limits only.
    demo_valid_to=datetime(2099,12,31,23,59,59)
    spec = Specification(material_id=mats[0].id, version="V1", status="APPROVED", effective_to=demo_valid_to, approved_at=datetime.utcnow())
    db.add(spec); db.flush()
    limits = {
        "SI": (Decimal("70"), Decimal("75")),
        "C": (None, Decimal("0.15")),
        "P": (None, Decimal("0.05")),
        "S": (None, Decimal("0.05")),
    }
    for i,a in enumerate(attrs):
        if a.attribute_code in limits:
            l,u=limits[a.attribute_code]
            db.add(SpecificationAttribute(specification_id=spec.id, attribute_id=a.id, lsl=l, usl=u, display_sequence=i+1))
    # Generic demo specifications for remaining materials.
    for m in mats[1:]:
        s=Specification(material_id=m.id, version="V1", status="APPROVED", effective_to=demo_valid_to, approved_at=datetime.utcnow())
        db.add(s); db.flush()
        for i,a in enumerate(attrs[:3]):
            db.add(SpecificationAttribute(specification_id=s.id, attribute_id=a.id, lsl=None, usl=Decimal("99.999"), display_sequence=i+1))
    db.commit()
