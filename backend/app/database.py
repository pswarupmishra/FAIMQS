from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./fa_iqm.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def ensure_schema_extensions():
    """Apply small additive migrations while the MVP does not yet use Alembic."""
    columns = {column["name"] for column in inspect(engine).get_columns("quality_attributes")}
    with engine.begin() as connection:
        if "group_id" not in columns:
            connection.execute(text("ALTER TABLE quality_attributes ADD COLUMN group_id VARCHAR"))
        if "category_options" not in columns:
            connection.execute(text("ALTER TABLE quality_attributes ADD COLUMN category_options TEXT"))
    material_columns = {column["name"] for column in inspect(engine).get_columns("materials")}
    with engine.begin() as connection:
        if "material_name" not in material_columns:
            connection.execute(text("ALTER TABLE materials ADD COLUMN material_name VARCHAR"))
            connection.execute(text("UPDATE materials SET material_name = material_description WHERE material_name IS NULL"))
    receipt_columns = {column["name"] for column in inspect(engine).get_columns("receipts")}
    with engine.begin() as connection:
        if "sms_code" not in receipt_columns:
            connection.execute(text("ALTER TABLE receipts ADD COLUMN sms_code VARCHAR"))
        if "plant_id" not in receipt_columns:
            connection.execute(text("ALTER TABLE receipts ADD COLUMN plant_id VARCHAR"))
        if "sms_id" not in receipt_columns:
            connection.execute(text("ALTER TABLE receipts ADD COLUMN sms_id VARCHAR"))
        if "store_id" not in receipt_columns:
            connection.execute(text("ALTER TABLE receipts ADD COLUMN store_id VARCHAR"))
    specification_columns = {column["name"] for column in inspect(engine).get_columns("specification_attributes")}
    with engine.begin() as connection:
        if "aim_value" not in specification_columns:
            connection.execute(text("ALTER TABLE specification_attributes ADD COLUMN aim_value NUMERIC(18,6)"))
        if "target_value" not in specification_columns:
            connection.execute(text("ALTER TABLE specification_attributes ADD COLUMN target_value VARCHAR"))
    specification_master_columns = {column["name"] for column in inspect(engine).get_columns("specifications")}
    with engine.begin() as connection:
        if "created_at" not in specification_master_columns:
            connection.execute(text("ALTER TABLE specifications ADD COLUMN created_at DATETIME"))
            connection.execute(text("UPDATE specifications SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
        if "approved_at" not in specification_master_columns:
            connection.execute(text("ALTER TABLE specifications ADD COLUMN approved_at DATETIME"))
            connection.execute(text("UPDATE specifications SET approved_at = created_at WHERE status = 'APPROVED' AND approved_at IS NULL"))
        connection.execute(text("UPDATE specifications SET effective_to = '2099-12-31 23:59:59' WHERE effective_to IS NULL"))
        has_supplier_scope = "supplier_id" in specification_master_columns
        rows = connection.execute(text(
            "SELECT id, material_id FROM specifications "
            "ORDER BY material_id, created_at, id"
        )).mappings().all()
        scopes = {}
        for row in rows:
            scopes.setdefault(row["material_id"], []).append(row["id"])
        for specification_ids in scopes.values():
            for index, specification_id in enumerate(specification_ids, start=1):
                status = "APPROVED" if index == len(specification_ids) else "APPROVED_HISTORY"
                connection.execute(text(
                    "UPDATE specifications SET version = :version, status = :status, "
                    "approved_at = COALESCE(approved_at, created_at) WHERE id = :id"
                ), {"version": f"V{index}", "status": status, "id": specification_id})
        if has_supplier_scope:
            connection.execute(text("UPDATE specifications SET supplier_id = NULL WHERE supplier_id IS NOT NULL"))
    log_columns = {column["name"] for column in inspect(engine).get_columns("specification_version_logs")}
    if "supplier_id" in log_columns:
        with engine.begin() as connection:
            connection.execute(text("UPDATE specification_version_logs SET supplier_id = NULL WHERE supplier_id IS NOT NULL"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
