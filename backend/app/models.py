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

class QualityAttribute(Base):
    __tablename__ = "quality_attributes"
    id = Column(String, primary_key=True, default=uid)
    attribute_code = Column(String, unique=True, nullable=False)
    attribute_name = Column(String, nullable=False)
    data_type = Column(String, default="NUMERIC")
    uom = Column(String, nullable=True)
    precision_scale = Column(Integer, default=3)
    test_method = Column(String, nullable=True)
    active = Column(Boolean, default=True)

class Specification(Base):
    __tablename__ = "specifications"
    id = Column(String, primary_key=True, default=uid)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    supplier_id = Column(String, ForeignKey("suppliers.id"), nullable=True)
    version = Column(String, nullable=False)
    status = Column(String, default="APPROVED")
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_to = Column(DateTime, nullable=True)
    material = relationship("Material")
    supplier = relationship("Supplier")
    attributes = relationship("SpecificationAttribute", cascade="all, delete-orphan")

class SpecificationAttribute(Base):
    __tablename__ = "specification_attributes"
    id = Column(String, primary_key=True, default=uid)
    specification_id = Column(String, ForeignKey("specifications.id"), nullable=False)
    attribute_id = Column(String, ForeignKey("quality_attributes.id"), nullable=False)
    mandatory = Column(Boolean, default=True)
    lsl = Column(Numeric(18,6), nullable=True)
    usl = Column(Numeric(18,6), nullable=True)
    display_sequence = Column(Integer, default=1)
    attribute = relationship("QualityAttribute")

class Receipt(Base):
    __tablename__ = "receipts"
    id = Column(String, primary_key=True, default=uid)
    receipt_no = Column(String, unique=True, nullable=False, index=True)
    plant_code = Column(String, default="VJNR")
    store_code = Column(String, default="FA_STORE")
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
    samples = relationship("Sample", cascade="all, delete-orphan")

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
    results = relationship("TestResult", cascade="all, delete-orphan")

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
    specification_attribute = relationship("SpecificationAttribute")

class Disposition(Base):
    __tablename__ = "quality_dispositions"
    id = Column(String, primary_key=True, default=uid)
    receipt_id = Column(String, ForeignKey("receipts.id"), nullable=False)
    disposition = Column(String, nullable=False)
    reason_text = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)
