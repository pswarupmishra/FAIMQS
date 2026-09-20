import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import insert

from .models import (
    AttentionConfigAudit, AttentionEngineConfig, AttentionEvent, AttentionRunLog,
    AttributeGroup, Disposition, MasterResetArchive, Material, Plant, QualityAttribute,
    Receipt, Sample, SmsLocation, Specification, SpecificationAttribute,
    SpecificationVersionLog, StoreLocation, Supplier, TestResult,
)


def new_id():
    return str(uuid.uuid4())


def clear_all_data(db):
    """Delete application data in dependency order."""
    models = [
        AttentionEvent, AttentionRunLog, AttentionConfigAudit, AttentionEngineConfig,
        Disposition, TestResult, Sample, Receipt, SpecificationVersionLog,
        SpecificationAttribute, Specification, QualityAttribute, AttributeGroup,
        StoreLocation, SmsLocation, Plant, Supplier, Material, MasterResetArchive,
    ]
    counts = {}
    for model in models:
        counts[model.__tablename__] = db.query(model).delete(synchronize_session=False)
    db.commit()
    return counts


def _chunks(rows, size=1500):
    for index in range(0, len(rows), size):
        yield rows[index:index + size]


def load_demo_data(db, sample_count=50_100):
    clear_all_data(db)
    rng = random.Random(20260920)
    now = datetime.utcnow()

    plant_id, sms_id, store_id = new_id(), new_id(), new_id()
    db.execute(insert(Plant), [{"id": plant_id, "plant_code": "VJNR", "plant_name": "Vijayanagar Works", "active": True}])
    db.execute(insert(SmsLocation), [{"id": sms_id, "plant_id": plant_id, "sms_code": "SMS1", "sms_name": "Steel Melting Shop 1", "active": True}])
    db.execute(insert(StoreLocation), [{"id": store_id, "sms_id": sms_id, "store_code": "FA_STORE", "store_name": "Ferro Alloy Store", "active": True}])

    material_defs = [
        ("FA000123", "Ferro Silicon", {"SI": (70.0, 72.5, 75.0), "C": (0.0, 0.10, 0.20), "P": (0.0, 0.035, 0.05), "S": (0.0, 0.025, 0.04), "AL": (0.0, 1.2, 2.0)}),
        ("FA000124", "High Carbon Ferro Manganese", {"MN": (70.0, 75.0, 80.0), "C": (6.0, 7.0, 8.0), "SI": (0.0, 1.2, 2.0), "P": (0.0, 0.25, 0.35), "S": (0.0, 0.025, 0.05)}),
        ("FA000125", "Silico Manganese", {"MN": (60.0, 65.0, 70.0), "SI": (14.0, 16.5, 19.0), "C": (0.0, 1.5, 2.0), "P": (0.0, 0.20, 0.30), "S": (0.0, 0.025, 0.04)}),
        ("FA000126", "High Carbon Ferro Chrome", {"CR": (60.0, 65.0, 70.0), "C": (6.0, 7.0, 8.0), "SI": (0.0, 2.0, 4.0), "P": (0.0, 0.03, 0.05), "S": (0.0, 0.03, 0.05)}),
        ("FA000127", "Low Carbon Ferro Chrome", {"CR": (60.0, 65.0, 70.0), "C": (0.0, 0.05, 0.10), "SI": (0.0, 1.0, 2.0), "P": (0.0, 0.025, 0.04), "S": (0.0, 0.025, 0.04)}),
        ("FA000128", "Ferro Vanadium", {"V": (75.0, 78.0, 82.0), "C": (0.0, 0.15, 0.25), "SI": (0.0, 1.0, 2.0), "AL": (0.0, 1.0, 2.0), "P": (0.0, 0.05, 0.10)}),
        ("FA000129", "Ferro Molybdenum", {"MO": (60.0, 65.0, 70.0), "C": (0.0, 0.08, 0.15), "SI": (0.0, 0.8, 1.5), "P": (0.0, 0.03, 0.05), "S": (0.0, 0.05, 0.10)}),
        ("FA000130", "Ferro Titanium", {"TI": (65.0, 70.0, 75.0), "AL": (0.0, 4.0, 8.0), "SI": (0.0, 2.5, 5.0), "C": (0.0, 0.15, 0.25), "P": (0.0, 0.05, 0.10)}),
    ]
    supplier_names = [
        "Bharat Alloy Resources", "Deccan Ferro Minerals", "Eastern Metals & Alloys",
        "Hind Alloy Industries", "Kalinga Mineral Products", "Mahadev Ferro Alloys",
        "Narmada Metallurgical", "Odisha Alloy Corporation", "Raipur Ferro Products",
        "Shakti Minerals & Metals", "Southern Alloy Traders", "Western Ferro Resources",
    ]
    materials = [{"id": new_id(), "material_code": code, "material_name": name, "material_description": name, "material_category": "FERRO_ALLOY", "base_uom": "MT", "batch_managed": True, "active": True} for code, name, _ in material_defs]
    suppliers = [{"id": new_id(), "supplier_code": f"SUP{index:03d}", "supplier_name": name, "active": True} for index, name in enumerate(supplier_names, start=1)]
    db.execute(insert(Material), materials)
    db.execute(insert(Supplier), suppliers)

    group_id = new_id()
    db.execute(insert(AttributeGroup), [{"id": group_id, "group_code": "CHEMISTRY", "group_name": "Chemical Composition", "description": "Ferro-alloy chemistry attributes", "active": True}])
    attribute_names = {"SI": "Silicon", "MN": "Manganese", "C": "Carbon", "P": "Phosphorus", "S": "Sulphur", "CR": "Chromium", "V": "Vanadium", "MO": "Molybdenum", "TI": "Titanium", "AL": "Aluminium"}
    attributes = {code: {"id": new_id(), "group_id": group_id, "attribute_code": code, "attribute_name": name, "data_type": "NUMERIC", "uom": "%", "precision_scale": 3, "active": True} for code, name in attribute_names.items()}
    db.execute(insert(QualityAttribute), list(attributes.values()))

    specs, spec_attributes, spec_map = [], [], {}
    for material, (_, _, limits) in zip(materials, material_defs):
        spec_id = new_id(); spec_map[material["id"]] = {"id": spec_id, "attributes": []}
        specs.append({"id": spec_id, "material_id": material["id"], "version": "V1", "status": "APPROVED", "effective_from": now - timedelta(days=900), "effective_to": datetime(2099, 12, 31, 23, 59, 59), "created_at": now - timedelta(days=900), "approved_at": now - timedelta(days=900)})
        for sequence, (code, (lsl, aim, usl)) in enumerate(limits.items(), start=1):
            spec_attribute = {"id": new_id(), "specification_id": spec_id, "attribute_id": attributes[code]["id"], "mandatory": True, "lsl": lsl, "aim_value": aim, "usl": usl, "display_sequence": sequence}
            spec_attributes.append(spec_attribute); spec_map[material["id"]]["attributes"].append(spec_attribute)
    db.execute(insert(Specification), specs)
    db.execute(insert(SpecificationAttribute), spec_attributes)
    db.commit()

    receipt_rows, sample_rows, result_rows, disposition_rows = [], [], [], []
    failed_receipts = 0
    for index in range(1, sample_count + 1):
        material = rng.choice(materials); supplier = rng.choice(suppliers); spec = spec_map[material["id"]]
        receipt_id, sample_id = new_id(), new_id()
        received_at = now - timedelta(days=rng.randint(0, 729), minutes=rng.randint(0, 1439))
        supplier_lot = f"{supplier['supplier_code']}-{received_at:%y}-{rng.randint(1, 1400):04d}"
        values, has_failure = [], False
        for spec_attribute in spec["attributes"]:
            lsl, aim, usl = float(spec_attribute["lsl"]), float(spec_attribute["aim_value"]), float(spec_attribute["usl"])
            sigma = max((usl - lsl) / 8, 0.005)
            value = rng.gauss(aim, sigma)
            if rng.random() < 0.035:
                value = usl + sigma * rng.uniform(0.3, 2.5) if rng.random() < 0.65 else lsl - sigma * rng.uniform(0.3, 2.0)
            evaluation = "PASS" if lsl <= value <= usl else "FAIL"
            has_failure = has_failure or evaluation == "FAIL"
            values.append({"id": new_id(), "sample_id": sample_id, "specification_attribute_id": spec_attribute["id"], "numeric_result": round(value, 4), "evaluation_status": evaluation, "result_status": "APPROVED", "entered_at": received_at + timedelta(hours=rng.randint(4, 30))})
        if has_failure:
            failed_receipts += 1
            rejected = rng.random() < 0.12
            disposition_value = "REJECTED" if rejected else "ACCEPTED_WITH_DEVIATION"
            release_state = "REJECTED" if rejected else "RELEASED"
            reason = "Demo: chemistry outside specification; reviewed under deviation" if not rejected else "Demo: chemistry deviation not acceptable"
        else:
            disposition_value, release_state, reason = "ACCEPTED", "RELEASED", None
        receipt_rows.append({"id": receipt_id, "receipt_no": f"FA-RCV-{received_at:%Y%m%d}-{index:05d}", "plant_code": "VJNR", "sms_code": "SMS1", "store_code": "FA_STORE", "plant_id": plant_id, "sms_id": sms_id, "store_id": store_id, "material_id": material["id"], "supplier_id": supplier["id"], "specification_id": spec["id"], "supplier_batch_no": supplier_lot, "internal_batch_no": f"IB-{received_at:%y%m}-{index:06d}", "po_no": f"PO-{received_at:%Y}-{rng.randint(1000, 9999)}", "grn_no": f"GRN-{received_at:%Y}-{index:06d}", "vehicle_no": f"KA-{rng.randint(10, 45):02d}-{rng.choice('ABCDEFGH')}-{rng.randint(1000, 9999)}", "quantity": round(rng.uniform(8, 42), 3), "uom": "MT", "receipt_datetime": received_at, "inspection_status": disposition_value, "release_state": release_state})
        sample_rows.append({"id": sample_id, "sample_no": f"FA-VJNR-{index:06d}", "receipt_id": receipt_id, "sample_type": "INITIAL", "sample_status": "RESULTS_APPROVED", "sample_datetime": received_at + timedelta(hours=2), "sampling_location": "Ferro Alloy Store", "sampling_method": "Composite"})
        result_rows.extend(values)
        disposition_rows.append({"id": new_id(), "receipt_id": receipt_id, "disposition": disposition_value, "reason_text": reason, "decided_at": received_at + timedelta(hours=32)})
        if len(receipt_rows) >= 1000:
            db.execute(insert(Receipt), receipt_rows); db.execute(insert(Sample), sample_rows)
            for chunk in _chunks(result_rows): db.execute(insert(TestResult), chunk)
            db.execute(insert(Disposition), disposition_rows)
            db.commit(); receipt_rows, sample_rows, result_rows, disposition_rows = [], [], [], []
    if receipt_rows:
        db.execute(insert(Receipt), receipt_rows); db.execute(insert(Sample), sample_rows)
        for chunk in _chunks(result_rows): db.execute(insert(TestResult), chunk)
        db.execute(insert(Disposition), disposition_rows); db.commit()
    return {"materials": len(materials), "suppliers": len(suppliers), "samples": sample_count, "test_results": sample_count * 5, "receipts_with_exceptions": failed_receipts}
