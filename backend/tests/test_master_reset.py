import unittest
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import current_master_query, reset_masters
from app.models import Material, Receipt, Specification, Supplier


class MasterResetTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_reset_hides_masters_and_preserves_receipt_links(self):
        material = Material(
            material_code="MAT-1",
            material_name="Material One",
            material_description="Material One",
        )
        supplier = Supplier(supplier_code="SUP-1", supplier_name="Supplier One")
        self.db.add_all([material, supplier])
        self.db.flush()
        specification = Specification(
            material_id=material.id,
            version="V1",
            status="APPROVED",
            created_at=datetime(2026, 1, 1),
        )
        self.db.add(specification)
        self.db.flush()
        receipt = Receipt(
            receipt_no="RCV-1",
            material_id=material.id,
            supplier_id=supplier.id,
            specification_id=specification.id,
            supplier_batch_no="SB-1",
            internal_batch_no="IB-1",
            po_no="PO-1",
            quantity=Decimal("10"),
        )
        self.db.add(receipt)
        self.db.commit()

        reset_masters(self.db)
        self.db.expire_all()

        self.assertEqual(1, self.db.query(Receipt).count())
        saved = self.db.query(Receipt).one()
        self.assertEqual("Material One", saved.material.material_name)
        self.assertEqual("Supplier One", saved.supplier.supplier_name)
        self.assertEqual("V1", saved.specification.version)
        self.assertEqual(0, current_master_query(self.db, Material, "material").count())
        self.assertEqual(0, current_master_query(self.db, Supplier, "supplier").count())
        self.assertEqual(0, current_master_query(self.db, Specification, "specification").count())


if __name__ == "__main__":
    unittest.main()
