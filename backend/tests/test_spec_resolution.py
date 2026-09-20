import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import resolve_spec
from app.models import Material, Specification, Supplier


class SpecificationResolutionTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.material = Material(material_code="TEST-MAT", material_name="Test Material", material_description="Test Material")
        self.supplier = Supplier(supplier_code="TEST-SUP", supplier_name="Test Supplier")
        self.db.add_all([self.material, self.supplier])
        self.db.flush()

    def tearDown(self):
        self.db.close()

    def test_latest_version_existing_at_transaction_time_is_selected(self):
        valid_from = datetime(2026, 1, 1)
        valid_to = datetime(2026, 12, 31, 23, 59, 59)
        first_approval = datetime(2026, 1, 2)
        second_approval = datetime(2026, 4, 1)
        v1 = Specification(material_id=self.material.id, version="V1", status="APPROVED_HISTORY", effective_from=valid_from, effective_to=valid_to, created_at=first_approval, approved_at=first_approval)
        v2 = Specification(material_id=self.material.id, version="V2", status="APPROVED", effective_from=valid_from, effective_to=valid_to, created_at=second_approval, approved_at=second_approval)
        draft = Specification(material_id=self.material.id, version="3.0", status="DRAFT", effective_from=valid_from, effective_to=valid_to)
        self.db.add_all([v1, v2, draft])
        self.db.commit()

        historical = resolve_spec(self.db, self.material.id, self.supplier.id, second_approval - timedelta(seconds=1))
        current = resolve_spec(self.db, self.material.id, self.supplier.id, second_approval + timedelta(seconds=1))

        self.assertEqual("V1", historical.version)
        self.assertEqual("V2", current.version)

    def test_draft_version_is_never_selected(self):
        now = datetime(2026, 6, 1)
        self.db.add(Specification(material_id=self.material.id, version="DRAFT", status="DRAFT", effective_from=now - timedelta(days=1), effective_to=now + timedelta(days=1)))
        self.db.commit()

        self.assertIsNone(resolve_spec(self.db, self.material.id, self.supplier.id, now))


if __name__ == "__main__":
    unittest.main()
