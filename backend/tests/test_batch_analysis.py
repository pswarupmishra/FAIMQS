import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import batch_analysis, supplier_performance_report
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
        return batch_analysis(
            reference_fields="supplier_batch_no", consolidation=policy, db=self.db,
        )

    def test_summary_can_skip_large_series_payload(self):
        data = batch_analysis(
            reference_fields="supplier_batch_no", consolidation="ALL",
            include_series=False, db=self.db,
        )
        self.assertEqual(1, len(data["batches"]))
        self.assertEqual([], data["series"])

    def test_selected_reference_only_returns_its_series(self):
        data = batch_analysis(
            reference_fields="supplier_batch_no", consolidation="ALL",
            selected_reference="LOT-1", db=self.db,
        )
        self.assertEqual(["LOT-1"], [batch["reference_id"] for batch in data["batches"]])
        self.assertEqual(2, len(data["series"][0]["points"]))

    def test_all_keeps_every_observation(self):
        data = self.analyze("ALL")
        self.assertEqual(1, len(data["batches"]))
        self.assertEqual(2, data["batches"][0]["receipt_count"])
        self.assertEqual([10.0, 20.0], [point["value"] for point in data["series"][0]["points"]])
        point = data["series"][0]["points"][0]
        self.assertEqual("SUP", point["supplier_code"])
        self.assertEqual("LOT-1", point["supplier_batch_no"])
        self.assertEqual("I1", point["internal_batch_no"])
        self.assertEqual("PO", point["po_no"])
        self.assertEqual("V1", point["specification_version"])

    def test_latest_keeps_newest_observation(self):
        data = self.analyze("LATEST")
        self.assertEqual(20.0, data["series"][0]["points"][0]["value"])
        self.assertEqual(2, data["series"][0]["points"][0]["source_count"])

    def test_mean_consolidates_matching_reference(self):
        data = self.analyze("MEAN")
        self.assertEqual(15.0, data["series"][0]["points"][0]["value"])
        self.assertEqual(2, data["series"][0]["points"][0]["source_count"])

    def test_supplier_performance_groups_outcomes_and_failed_attributes(self):
        receipts = self.db.query(Receipt).order_by(Receipt.receipt_no).all()
        receipts[0].inspection_status = "ACCEPTED_WITH_DEVIATION"
        receipts[1].inspection_status = "REJECTED"
        for result in self.db.query(TestResult).all():
            result.evaluation_status = "FAIL"
        self.db.commit()
        data = supplier_performance_report(db=self.db)
        self.assertEqual(2, data["summary"]["total"])
        self.assertEqual(1, data["summary"]["ACCEPTED_WITH_DEVIATION"])
        self.assertEqual(1, data["summary"]["REJECTED"])
        self.assertEqual(2, data["by_supplier"][0]["total"])
        self.assertEqual({"ACCEPTED_WITH_DEVIATION", "REJECTED"}, {row["quality_state"] for row in data["attribute_contributors"]})


if __name__ == "__main__":
    unittest.main()
