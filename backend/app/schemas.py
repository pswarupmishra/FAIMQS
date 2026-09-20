from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class MaterialOut(ORM):
    id: str
    material_code: str
    material_name: str
    material_description: str
    base_uom: str
    active: bool = True

class MaterialCreate(BaseModel):
    material_code: str
    material_name: str
    material_description: str
    base_uom: str = "MT"
    batch_managed: bool = True
    active: bool = True

    @field_validator("material_code", "material_name")
    @classmethod
    def validate_required_material_text(cls, value: str):
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value.strip()

class SupplierOut(ORM):
    id: str
    supplier_code: str
    supplier_name: str
    active: bool = True

class SupplierCreate(BaseModel):
    supplier_code: str
    supplier_name: str
    active: bool = True

class SupplierStatusUpdate(BaseModel):
    active: bool

class PlantCreate(BaseModel):
    plant_code: str
    plant_name: str
    active: bool = True

class SmsLocationCreate(BaseModel):
    plant_id: str
    sms_code: str
    sms_name: str
    active: bool = True

class StoreLocationCreate(BaseModel):
    sms_id: str
    store_code: str
    store_name: str
    active: bool = True

class AttributeGroupCreate(BaseModel):
    group_code: str
    group_name: str
    description: Optional[str] = None
    active: bool = True

    @field_validator("group_code", "group_name")
    @classmethod
    def validate_required_group_text(cls, value: str):
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value.strip()

class QualityAttributeCreate(BaseModel):
    group_id: str
    attribute_code: str
    attribute_name: str
    uom: Optional[str] = None
    data_type: str = "NUMERIC"
    precision_scale: int = 3
    test_method: Optional[str] = None
    category_options: list[str] = []
    active: bool = True

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, value: str):
        value = value.strip().upper()
        if value not in {"NUMERIC", "CATEGORY", "BOOLEAN"}:
            raise ValueError("Attribute type must be NUMERIC, CATEGORY, or BOOLEAN")
        return value

    @model_validator(mode="after")
    def validate_category_options(self):
        self.category_options = [x.strip() for x in self.category_options if x.strip()]
        if self.data_type == "CATEGORY" and not self.category_options:
            raise ValueError("Category attributes require at least one allowed value")
        if self.data_type != "CATEGORY":
            self.category_options = []
        if self.data_type != "NUMERIC":
            self.uom = None
        return self

class SpecAttributeIn(BaseModel):
    attribute_id: str
    mandatory: bool = True
    lsl: Optional[Decimal] = None
    usl: Optional[Decimal] = None
    aim_value: Optional[Decimal] = None
    target_value: Optional[str] = None
    display_sequence: int = 1

    @model_validator(mode="after")
    def validate_limits(self):
        if self.lsl is not None and self.usl is not None and self.lsl > self.usl:
            raise ValueError("Lower specification limit cannot exceed upper specification limit")
        if self.aim_value is not None and self.lsl is not None and self.aim_value < self.lsl:
            raise ValueError("Aim value cannot be lower than the minimum value")
        if self.aim_value is not None and self.usl is not None and self.aim_value > self.usl:
            raise ValueError("Aim value cannot exceed the maximum value")
        return self

class SpecificationCreate(BaseModel):
    material_id: str
    version: Optional[str] = None
    status: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    attributes: list[SpecAttributeIn]

    @model_validator(mode="after")
    def validate_dates(self):
        if self.effective_from is not None and self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("Effective To must be on or after Effective From")
        if not self.attributes:
            raise ValueError("At least one quality attribute is required")
        return self

class ReceiptCreate(BaseModel):
    plant_id: str
    sms_id: str
    store_id: str
    material_id: str
    supplier_id: str
    supplier_batch_no: str
    internal_batch_no: str
    po_no: str
    grn_no: Optional[str] = None
    vehicle_no: Optional[str] = None
    quantity: Decimal
    uom: str = "MT"
    receipt_datetime: Optional[datetime] = None
    remarks: Optional[str] = None

class ReceiptOut(ORM):
    id: str
    receipt_no: str
    supplier_batch_no: str
    internal_batch_no: str
    po_no: str
    quantity: Decimal
    uom: str
    inspection_status: str
    release_state: str
    receipt_datetime: datetime
    specification_id: str
    specification_version: str
    material: MaterialOut
    supplier: SupplierOut

class SampleCreate(BaseModel):
    sample_type: str = "INITIAL"
    sampling_location: str = "Ferro Alloy Store"
    sampling_method: str = "Composite"
    remarks: Optional[str] = None

class ResultIn(BaseModel):
    specification_attribute_id: str
    numeric_result: Optional[Decimal] = None
    text_result: Optional[str] = None

class DispositionIn(BaseModel):
    disposition: str
    reason_text: Optional[str] = None
