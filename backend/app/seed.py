from decimal import Decimal
from sqlalchemy.orm import Session
from .models import Material, Supplier, QualityAttribute, Specification, SpecificationAttribute

def seed(db: Session):
    if db.query(Material).count():
        return
    mats = [
        Material(material_code="FA000123", material_description="Ferro Silicon"),
        Material(material_code="FA000124", material_description="Ferro Manganese"),
        Material(material_code="FA000125", material_description="Silico Manganese"),
        Material(material_code="FA000126", material_description="Ferro Chrome"),
        Material(material_code="FA000127", material_description="Ferro Vanadium"),
    ]
    sups = [
        Supplier(supplier_code="SUP001", supplier_name="Demo Alloy Supplier A"),
        Supplier(supplier_code="SUP002", supplier_name="Demo Alloy Supplier B"),
        Supplier(supplier_code="SUP003", supplier_name="Demo Metals Supplier C"),
        Supplier(supplier_code="SUP004", supplier_name="Demo Minerals Supplier D"),
    ]
    attrs = [
        QualityAttribute(attribute_code="SI", attribute_name="Silicon", uom="%"),
        QualityAttribute(attribute_code="MN", attribute_name="Manganese", uom="%"),
        QualityAttribute(attribute_code="C", attribute_name="Carbon", uom="%"),
        QualityAttribute(attribute_code="P", attribute_name="Phosphorus", uom="%"),
        QualityAttribute(attribute_code="S", attribute_name="Sulphur", uom="%"),
    ]
    db.add_all(mats+sups+attrs); db.flush()
    # DEMO limits only.
    spec = Specification(material_id=mats[0].id, version="DEMO-1.0", status="APPROVED")
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
        s=Specification(material_id=m.id, version="DEMO-1.0", status="APPROVED")
        db.add(s); db.flush()
        for i,a in enumerate(attrs[:3]):
            db.add(SpecificationAttribute(specification_id=s.id, attribute_id=a.id, lsl=None, usl=Decimal("99.999"), display_sequence=i+1))
    db.commit()
