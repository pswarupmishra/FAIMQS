import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import batch_analysis
from app.models import (
    Material, QualityAttribute, Receipt, Sample, Specification,
    SpecificationAttribute, Supplier, TestResult,
)


class BatchAnalysisTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        material = Material(material_code="MAT", material_name="Material", material_description="Material")
        supplier = Supplier(supplier_code="SUP", supplier_name="Supplier")
        attribute = QualityAttribute(attribute_code="SI", attribute_name="Silicon", data_type="NUMERIC", uom="%")
        self.db.add_all([material, supplier, attribute]); self.db.flush()
        specification = Specification(material_id=material.id, version="V1", status="APPROVED", created_at=datetime(2026, 1, 1))
        self.db.add(specification); self.db.flush()
        spec_attribute = SpecificationAttribute(specification_id=specification.id, attribute_id=attribute.id, lsl=Decimal("5"), aim_value=Decimal("15"), usl=Decimal("25"))
        self.db.add(spec_attribute); self.db.flush()
        for index, value in enumerate((Decimal("10"), Decimal("20")), start=1):
            at = datetime(2026, 1, index)
            receipt = Receipt(receipt_no=f"R{index}", material_id=material.id, supplier_id=supplier.id, specification_id=specification.id, supplier_batch_no="LOT-1", internal_batch_no=f"I{index}", po_no="PO", quantity=Decimal("1"), receipt_datetime=at)
            self.db.add(receipt); self.db.flush()
            sample = Sample(sample_no=f"S{index}", receipt_id=receipt.id)
            self.db.add(sample); self.db.flush()
            self.db.add(TestResult(sample_id=sample.id, specification_attribute_id=spec_attribute.id, numeric_result=value, entered_at=at + timedelta(hours=1)))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def analyze(self, policy):
        return batch_analysis("supplier_batch_no", policy, None, None, None, self.db)

    def test_all_keeps_every_observation(self):
        data = self.analyze("ALL")
        self.assertEqual(1, len(data["batches"]))
        self.assertEqual(2, data["batches"][0]["receipt_count"])
        self.assertEqual([10.0, 20.0], [point["value"] for point in data["series"][0]["points"]])

    def test_latest_keeps_newest_observation(self):
        data = self.analyze("LATEST")
        self.assertEqual(20.0, data["series"][0]["points"][0]["value"])
        self.assertEqual(2, data["series"][0]["points"][0]["source_count"])

    def test_mean_consolidates_matching_reference(self):
        data = self.analyze("MEAN")
        self.assertEqual(15.0, data["series"][0]["points"][0]["value"])
        self.assertEqual(2, data["series"][0]["points"][0]["source_count"])


if __name__ == "__main__":
    unittest.main()
