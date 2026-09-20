import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Integer, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

def uid():
    return str(uuid.uuid4())

class Material(Base):
    __tablename__ = "materials"
    id = Column(String, primary_key=True, default=uid)
    material_code = Column(String, unique=True, nullable=False, index=True)
    material_name = Column(String, nullable=False)
    material_description = Column(String, nullable=False)
    material_category = Column(String, default="FERRO_ALLOY")
    base_uom = Column(String, default="MT")
    batch_managed = Column(Boolean, default=True)
    active = Column(Boolean, default=True)

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(String, primary_key=True, default=uid)
    supplier_code = Column(String, unique=True, nullable=False, index=True)
    supplier_name = Column(String, nullable=False)
    active = Column(Boolean, default=True)

class Plant(Base):
    __tablename__ = "plants"
    id = Column(String, primary_key=True, default=uid)
    plant_code = Column(String, unique=True, nullable=False, index=True)
    plant_name = Column(String, nullable=False)
    active = Column(Boolean, default=True)

class SmsLocation(Base):
    __tablename__ = "sms_locations"
    __table_args__ = (UniqueConstraint("plant_id", "sms_code", name="uq_plant_sms_code"),)
    id = Column(String, primary_key=True, default=uid)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=False)
    sms_code = Column(String, nullable=False)
    sms_name = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    plant = relationship("Plant")

class StoreLocation(Base):
    __tablename__ = "store_locations"
    __table_args__ = (UniqueConstraint("sms_id", "store_code", name="uq_sms_store_code"),)
    id = Column(String, primary_key=True, default=uid)
    sms_id = Column(String, ForeignKey("sms_locations.id"), nullable=False)
    store_code = Column(String, nullable=False)
    store_name = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    sms = relationship("SmsLocation")

class AttributeGroup(Base):
    __tablename__ = "attribute_groups"
    id = Column(String, primary_key=True, default=uid)
    group_code = Column(String, unique=True, nullable=False, index=True)
    group_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True)

class QualityAttribute(Base):
    __tablename__ = "quality_attributes"
    id = Column(String, primary_key=True, default=uid)
    group_id = Column(String, ForeignKey("attribute_groups.id"), nullable=True)
    attribute_code = Column(String, unique=True, nullable=False)
    attribute_name = Column(String, nullable=False)
    data_type = Column(String, default="NUMERIC")
    uom = Column(String, nullable=True)
    precision_scale = Column(Integer, default=3)
    test_method = Column(String, nullable=True)
    category_options = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    group = relationship("AttributeGroup")

class Specification(Base):
    __tablename__ = "specifications"
    id = Column(String, primary_key=True, default=uid)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    version = Column(String, nullable=False)
    status = Column(String, default="APPROVED")
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    material = relationship("Material")
    attributes = relationship("SpecificationAttribute", cascade="all, delete-orphan")

class SpecificationAttribute(Base):
    __tablename__ = "specification_attributes"
    id = Column(String, primary_key=True, default=uid)
    specification_id = Column(String, ForeignKey("specifications.id"), nullable=False)
    attribute_id = Column(String, ForeignKey("quality_attributes.id"), nullable=False)
    mandatory = Column(Boolean, default=True)
    lsl = Column(Numeric(18,6), nullable=True)
    usl = Column(Numeric(18,6), nullable=True)
    aim_value = Column(Numeric(18,6), nullable=True)
    target_value = Column(String, nullable=True)
    display_sequence = Column(Integer, default=1)
    attribute = relationship("QualityAttribute")

class SpecificationVersionLog(Base):
    __tablename__ = "specification_version_logs"
    id = Column(String, primary_key=True, default=uid)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    previous_specification_id = Column(String, ForeignKey("specifications.id"), nullable=True)
    new_specification_id = Column(String, ForeignKey("specifications.id"), nullable=False)
    previous_version = Column(String, nullable=True)
    new_version = Column(String, nullable=False)
    change_summary = Column(Text, nullable=False)
    changed_by = Column(String, default="SYSTEM", nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    material = relationship("Material")

class MasterResetArchive(Base):
    """Hides reset master rows while preserving transaction foreign keys."""
    __tablename__ = "master_reset_archive"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_master_reset_entity"),)
    id = Column(String, primary_key=True, default=uid)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    reset_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Receipt(Base):
    __tablename__ = "receipts"
    id = Column(String, primary_key=True, default=uid)
    receipt_no = Column(String, unique=True, nullable=False, index=True)
    plant_code = Column(String, default="VJNR")
    sms_code = Column(String, nullable=True)
    store_code = Column(String, default="FA_STORE")
    plant_id = Column(String, ForeignKey("plants.id"), nullable=True)
    sms_id = Column(String, ForeignKey("sms_locations.id"), nullable=True)
    store_id = Column(String, ForeignKey("store_locations.id"), nullable=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)
    specification_id = Column(String, ForeignKey("specifications.id"), nullable=False)
    supplier_batch_no = Column(String, nullable=False, index=True)
    internal_batch_no = Column(String, nullable=False, index=True)
    po_no = Column(String, nullable=False)
    grn_no = Column(String, nullable=True)
    vehicle_no = Column(String, nullable=True)
    quantity = Column(Numeric(18,3), nullable=False)
    uom = Column(String, default="MT")
    receipt_datetime = Column(DateTime, default=datetime.utcnow)
    inspection_status = Column(String, default="DRAFT", index=True)
    release_state = Column(String, default="BLOCKED", index=True)
    remarks = Column(Text, nullable=True)
    material = relationship("Material")
    supplier = relationship("Supplier")
    specification = relationship("Specification")
    plant = relationship("Plant")
    sms = relationship("SmsLocation")
    store = relationship("StoreLocation")
    samples = relationship("Sample", cascade="all, delete-orphan")

    @property
    def specification_version(self):
        return self.specification.version if self.specification else None

class Sample(Base):
    __tablename__ = "samples"
    id = Column(String, primary_key=True, default=uid)
    sample_no = Column(String, unique=True, nullable=False, index=True)
    receipt_id = Column(String, ForeignKey("receipts.id"), nullable=False)
    parent_sample_id = Column(String, ForeignKey("samples.id"), nullable=True)
    sample_type = Column(String, default="INITIAL")
    sample_status = Column(String, default="CREATED")
    sample_datetime = Column(DateTime, default=datetime.utcnow)
    sampling_location = Column(String, default="Ferro Alloy Store")
    sampling_method = Column(String, default="Composite")
    remarks = Column(Text, nullable=True)
    results = relationship("TestResult", cascade="all, delete-orphan", back_populates="sample")

class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (UniqueConstraint("sample_id", "specification_attribute_id", name="uq_sample_attr"),)
    id = Column(String, primary_key=True, default=uid)
    sample_id = Column(String, ForeignKey("samples.id"), nullable=False)
    specification_attribute_id = Column(String, ForeignKey("specification_attributes.id"), nullable=False)
    numeric_result = Column(Numeric(18,6), nullable=True)
    text_result = Column(String, nullable=True)
    evaluation_status = Column(String, default="PENDING")
    result_status = Column(String, default="DRAFT")
    entered_at = Column(DateTime, default=datetime.utcnow)
    sample = relationship("Sample", back_populates="results")
    specification_attribute = relationship("SpecificationAttribute")

class Disposition(Base):
    __tablename__ = "quality_dispositions"
    id = Column(String, primary_key=True, default=uid)
    receipt_id = Column(String, ForeignKey("receipts.id"), nullable=False)
    disposition = Column(String, nullable=False)
    reason_text = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)

class AttentionEngineConfig(Base):
    __tablename__ = "attention_engine_config"
    id = Column(String, primary_key=True, default=uid)
    config_name = Column(String, default="Global", nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    test_selection_mode = Column(String, default="LATEST_PER_REFERENCE", nullable=False)
    numeric_aggregate_method = Column(String, default="MEAN", nullable=False)
    baseline_window_n = Column(Integer, default=30, nullable=False)
    min_baseline_n = Column(Integer, default=20, nullable=False)
    near_spec_margin_type = Column(String, default="PERCENT_TOLERANCE", nullable=False)
    near_spec_margin_value = Column(Numeric(18,6), default=10, nullable=False)
    reference_fields_json = Column(Text, default='["supplier_batch_no"]', nullable=False)
    fallback_fields_json = Column(Text, default='["internal_batch_no","receipt_no"]', nullable=False)
    include_sample_types_json = Column(Text, default='["INITIAL","RETEST","CONFIRMATORY"]', nullable=False)
    include_result_statuses_json = Column(Text, default='["SUBMITTED","APPROVED"]', nullable=False)
    rules_json = Column(Text, default='{"SPEC_FAIL":true,"NEAR_SPEC":true,"WE1":true,"WE2":true,"WE3":true,"WE4":true,"CONSECUTIVE_ADVERSE":true,"ADVERSE_RATE":true}', nullable=False)
    discrete_json = Column(Text, default='{"consecutive_n":3,"rate_window_n":10,"warning_rate":0.2,"critical_rate":0.4}', nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AttentionConfigAudit(Base):
    __tablename__ = "attention_config_audit"
    id = Column(String, primary_key=True, default=uid)
    config_id = Column(String, ForeignKey("attention_engine_config.id"), nullable=False)
    version = Column(Integer, nullable=False)
    before_json = Column(Text, nullable=True)
    after_json = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    changed_by = Column(String, default="SYSTEM", nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class AttentionEvent(Base):
    __tablename__ = "attention_events"
    id = Column(String, primary_key=True, default=uid)
    fingerprint = Column(String, unique=True, nullable=False, index=True)
    event_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=False)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    attribute_id = Column(String, ForeignKey("quality_attributes.id"), nullable=False)
    reference_id = Column(String, nullable=False)
    receipt_id = Column(String, ForeignKey("receipts.id"), nullable=False)
    sample_id = Column(String, ForeignKey("samples.id"), nullable=False)
    test_result_id = Column(String, ForeignKey("test_results.id"), nullable=False)
    specification_id = Column(String, ForeignKey("specifications.id"), nullable=False)
    rule_code = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, default="OPEN", nullable=False)
    observed_value = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    lsl = Column(Numeric(18,6), nullable=True)
    usl = Column(Numeric(18,6), nullable=True)
    target_value = Column(String, nullable=True)
    baseline_mean = Column(Numeric(18,6), nullable=True)
    baseline_sigma = Column(Numeric(18,6), nullable=True)
    baseline_n = Column(Integer, nullable=True)
    config_version = Column(Integer, nullable=False)
    rule_evidence_json = Column(Text, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    supplier = relationship("Supplier")
    material = relationship("Material")
    attribute = relationship("QualityAttribute")

class AttentionRunLog(Base):
    __tablename__ = "attention_run_log"
    id = Column(String, primary_key=True, default=uid)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="RUNNING", nullable=False)
    records_scanned = Column(Integer, default=0, nullable=False)
    observations_used = Column(Integer, default=0, nullable=False)
    events_created = Column(Integer, default=0, nullable=False)
    config_version = Column(Integer, nullable=False)
    error_text = Column(Text, nullable=True)
