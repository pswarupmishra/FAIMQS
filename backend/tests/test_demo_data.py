import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.demo_data import clear_all_data, load_demo_data
from app.models import Material, Receipt, Sample, Supplier, TestResult


class DemoDataTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_demo_generator_creates_complete_quality_transactions(self):
        summary = load_demo_data(self.db, sample_count=25)
        self.assertEqual(8, summary["materials"])
        self.assertEqual(12, summary["suppliers"])
        self.assertEqual(25, self.db.query(Receipt).count())
        self.assertEqual(25, self.db.query(Sample).count())
        self.assertEqual(125, self.db.query(TestResult).count())
        self.assertTrue(all(sample.sample_status == "RESULTS_APPROVED" for sample in self.db.query(Sample).all()))

    def test_full_reset_removes_master_and_transaction_data(self):
        load_demo_data(self.db, sample_count=5)
        clear_all_data(self.db)
        self.assertEqual(0, self.db.query(Material).count())
        self.assertEqual(0, self.db.query(Supplier).count())
        self.assertEqual(0, self.db.query(Receipt).count())
        self.assertEqual(0, self.db.query(Sample).count())
        self.assertEqual(0, self.db.query(TestResult).count())


if __name__ == "__main__":
    unittest.main()
