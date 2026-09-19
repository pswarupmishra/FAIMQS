from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, model_validator

class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class MaterialOut(ORM):
    id: str
    material_code: str
    material_description: str
    base_uom: str
    active: bool = True

class MaterialCreate(BaseModel):
    material_code: str
    material_description: str
    base_uom: str = "MT"
    batch_managed: bool = True
    active: bool = True

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

class QualityAttributeCreate(BaseModel):
    attribute_code: str
    attribute_name: str
    uom: str | None = None
    data_type: str = "NUMERIC"
    precision_scale: int = 3
    test_method: str | None = None
    active: bool = True

class SpecAttributeIn(BaseModel):
    attribute_id: str
    mandatory: bool = True
    lsl: Decimal | None = None
    usl: Decimal | None = None
    display_sequence: int = 1

    @model_validator(mode="after")
    def validate_limits(self):
        if self.lsl is not None and self.usl is not None and self.lsl > self.usl:
            raise ValueError("Lower specification limit cannot exceed upper specification limit")
        return self

class SpecificationCreate(BaseModel):
    material_id: str
    supplier_id: str | None = None
    version: str
    status: str = "APPROVED"
    effective_from: datetime
    effective_to: datetime
    attributes: list[SpecAttributeIn]

    @model_validator(mode="after")
    def validate_dates(self):
        if self.effective_to < self.effective_from:
            raise ValueError("Effective To must be on or after Effective From")
        if not self.attributes:
            raise ValueError("At least one quality attribute is required")
        return self

class ReceiptCreate(BaseModel):
    material_id: str
    supplier_id: str
    supplier_batch_no: str
    internal_batch_no: str
    po_no: str
    grn_no: str | None = None
    vehicle_no: str | None = None
    quantity: Decimal
    uom: str = "MT"
    receipt_datetime: datetime | None = None
    remarks: str | None = None

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
    material: MaterialOut
    supplier: SupplierOut

class SampleCreate(BaseModel):
    sample_type: str = "INITIAL"
    sampling_location: str = "Ferro Alloy Store"
    sampling_method: str = "Composite"
    remarks: str | None = None

class ResultIn(BaseModel):
    specification_attribute_id: str
    numeric_result: Decimal | None = None
    text_result: str | None = None

class DispositionIn(BaseModel):
    disposition: str
    reason_text: str | None = None
