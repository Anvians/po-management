from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
import random, string, datetime

from app.database import get_db
from app.models import PurchaseOrder, PurchaseOrderItem, Product, POStatus
from app.schemas import PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse
from app.routers.auth import verify_token

router = APIRouter()
TAX_RATE = 0.05  # 5%


def _generate_reference() -> str:
    """Generate unique PO reference like PO-20240101-ABCD."""
    date_str = datetime.date.today().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"PO-{date_str}-{suffix}"


def _calculate_totals(items_data: list, db: Session):
    """
    Core business logic: compute subtotal, 5% tax, and total.
    Returns (subtotal, tax_amount, total_amount, enriched_items).
    """
    subtotal = 0.0
    enriched = []

    for item in items_data:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        line_total = round(product.unit_price * item.quantity, 2)
        subtotal += line_total
        enriched.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "unit_price": product.unit_price,
            "line_total": line_total,
        })

    subtotal = round(subtotal, 2)
    tax_amount = round(subtotal * TAX_RATE, 2)
    total_amount = round(subtotal + tax_amount, 2)
    return subtotal, tax_amount, total_amount, enriched


@router.get("/", response_model=List[PurchaseOrderResponse])
def list_purchase_orders(
    skip: int = 0,
    limit: int = 50,
    status: POStatus = None,
    db: Session = Depends(get_db),
):
    query = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.vendor),
        joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product)
    )
    if status:
        query = query.filter(PurchaseOrder.status == status)
    return query.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    po: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token)
):
    if not po.items:
        raise HTTPException(status_code=400, detail="Purchase order must have at least one item")

    subtotal, tax_amount, total_amount, enriched_items = _calculate_totals(po.items, db)

    # Ensure unique reference
    while True:
        ref = _generate_reference()
        if not db.query(PurchaseOrder).filter(PurchaseOrder.reference_no == ref).first():
            break

    db_po = PurchaseOrder(
        reference_no=ref,
        vendor_id=po.vendor_id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        notes=po.notes,
        status=POStatus.DRAFT,
    )
    db.add(db_po)
    db.flush()  # get db_po.id before committing

    for item_data in enriched_items:
        db.add(PurchaseOrderItem(purchase_order_id=db_po.id, **item_data))

    db.commit()
    db.refresh(db_po)

    return db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.vendor),
        joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product)
    ).filter(PurchaseOrder.id == db_po.id).first()


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def get_purchase_order(po_id: int, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.vendor),
        joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product)
    ).filter(PurchaseOrder.id == po_id).first()
    
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    return po


@router.patch("/{po_id}/status", response_model=PurchaseOrderResponse)
def update_po_status(
    po_id: int,
    update: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token)
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    
    if update.status:
        po.status = update.status
    if update.notes is not None:
        po.notes = update.notes
    
    db.commit()
    db.refresh(po)
    return po


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_order(
    po_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token)
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    if po.status not in [POStatus.DRAFT, POStatus.REJECTED]:
        raise HTTPException(status_code=400, detail="Only DRAFT or REJECTED orders can be deleted")
    
    db.delete(po)
    db.commit()
