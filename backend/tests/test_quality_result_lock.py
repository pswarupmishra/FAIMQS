import unittest
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import disposition, save_results
from app.models import Material, Receipt, Sample, Specification, Supplier
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
        self.receipt = Receipt(receipt_no="RCV", material_id=material.id, supplier_id=supplier.id, specification_id=specification.id, supplier_batch_no="B1", internal_batch_no="I1", po_no="PO1", quantity=Decimal("1"), inspection_status="UNDER_REVIEW")
        self.db.add(self.receipt); self.db.flush()
        self.sample = Sample(sample_no="S1", receipt_id=self.receipt.id, sample_status="RESULTS_SUBMITTED")
        self.db.add(self.sample); self.db.commit()

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


if __name__ == "__main__":
    unittest.main()
