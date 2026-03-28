from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.models import POStatus


# ── Vendor ──────────────────────────────────────────────────────────────────

class VendorBase(BaseModel):
    name: str
    contact: str
    email: EmailStr
    phone: Optional[str] = None
    rating: Optional[float] = Field(default=0.0, ge=0.0, le=5.0)


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)


class VendorResponse(VendorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Product ──────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    name: str
    sku: str
    category: Optional[str] = None
    unit_price: float = Field(gt=0)
    stock_level: Optional[int] = Field(default=0, ge=0)
    description: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = Field(default=None, gt=0)
    stock_level: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = None
    ai_description: Optional[str] = None


class ProductResponse(ProductBase):
    id: int
    ai_description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Purchase Order Item ───────────────────────────────────────────────────────

class POItemBase(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class POItemCreate(POItemBase):
    pass


class POItemResponse(POItemBase):
    id: int
    unit_price: float
    line_total: float
    product: ProductResponse

    class Config:
        from_attributes = True


# ── Purchase Order ────────────────────────────────────────────────────────────

class PurchaseOrderCreate(BaseModel):
    vendor_id: int
    items: List[POItemCreate]
    notes: Optional[str] = None


class PurchaseOrderUpdate(BaseModel):
    status: Optional[POStatus] = None
    notes: Optional[str] = None


class PurchaseOrderResponse(BaseModel):
    id: int
    reference_no: str
    vendor_id: int
    vendor: VendorResponse
    items: List[POItemResponse]
    subtotal: float
    tax_amount: float
    total_amount: float
    status: POStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class AIDescriptionRequest(BaseModel):
    product_name: str
    category: Optional[str] = "General"
