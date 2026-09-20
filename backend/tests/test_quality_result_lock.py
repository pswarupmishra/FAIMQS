import unittest
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import disposition, save_results
from app.models import Material, QualityAttribute, Receipt, Sample, Specification, SpecificationAttribute, Supplier, TestResult
from app.schemas import DispositionIn


class QualityResultLockTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        material = Material(material_code="MAT", material_name="Material", material_description="Material")
        supplier = Supplier(supplier_code="SUP", supplier_name="Supplier")
        self.db.add_all([material, supplier]); self.db.flush()
        specification = Specification(material_id=material.id, version="V1", status="APPROVED")
        self.db.add(specification); self.db.flush()
        attribute = QualityAttribute(attribute_code="SI", attribute_name="Silicon", data_type="NUMERIC", uom="%")
        self.db.add(attribute); self.db.flush()
        self.spec_attribute = SpecificationAttribute(specification_id=specification.id, attribute_id=attribute.id, mandatory=True, lsl=Decimal("70"), aim_value=Decimal("72.5"), usl=Decimal("75"))
        self.db.add(self.spec_attribute); self.db.flush()
        self.receipt = Receipt(receipt_no="RCV", material_id=material.id, supplier_id=supplier.id, specification_id=specification.id, supplier_batch_no="B1", internal_batch_no="I1", po_no="PO1", quantity=Decimal("1"), inspection_status="UNDER_REVIEW")
        self.db.add(self.receipt); self.db.flush()
        self.sample = Sample(sample_no="S1", receipt_id=self.receipt.id, sample_status="RESULTS_SUBMITTED")
        self.db.add(self.sample); self.db.flush()
        self.result = TestResult(sample_id=self.sample.id, specification_attribute_id=self.spec_attribute.id, numeric_result=Decimal("80"), evaluation_status="FAIL", result_status="APPROVED")
        self.db.add(self.result); self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_submitted_results_cannot_be_edited(self):
        with self.assertRaises(HTTPException) as raised:
            save_results(self.sample.id, [], self.db)
        self.assertEqual(409, raised.exception.status_code)

    def test_accept_with_deviation_releases_batch(self):
        result = disposition(self.receipt.id, DispositionIn(disposition="ACCEPTED_WITH_DEVIATION", reason_text="Approved engineering deviation"), self.db)
        self.assertEqual("ACCEPTED_WITH_DEVIATION", result["inspection_status"])
        self.assertEqual("RELEASED", result["release_state"])

    def test_accept_with_deviation_requires_reason(self):
        with self.assertRaises(HTTPException) as raised:
            disposition(self.receipt.id, DispositionIn(disposition="ACCEPTED_WITH_DEVIATION"), self.db)
        self.assertEqual(400, raised.exception.status_code)

    def test_normal_acceptance_requires_all_results_to_pass(self):
        with self.assertRaises(HTTPException) as raised:
            disposition(self.receipt.id, DispositionIn(disposition="ACCEPTED"), self.db)
        self.assertEqual(409, raised.exception.status_code)
        self.result.evaluation_status = "PASS"; self.db.commit()
        result = disposition(self.receipt.id, DispositionIn(disposition="ACCEPTED", reason_text="All results conform"), self.db)
        self.assertEqual("RELEASED", result["release_state"])

    def test_deviation_and_rejection_require_an_out_of_spec_result(self):
        self.result.evaluation_status = "PASS"; self.db.commit()
        for value in ("ACCEPTED_WITH_DEVIATION", "REJECTED"):
            with self.assertRaises(HTTPException) as raised:
                disposition(self.receipt.id, DispositionIn(disposition=value, reason_text="Review remark"), self.db)
            self.assertEqual(409, raised.exception.status_code)

    def test_rejection_with_failed_result_is_blocked_and_rejected(self):
        result = disposition(self.receipt.id, DispositionIn(disposition="REJECTED", reason_text="Deviation not acceptable"), self.db)
        self.assertEqual("REJECTED", result["inspection_status"])
        self.assertEqual("REJECTED", result["release_state"])


if __name__ == "__main__":
    unittest.main()
