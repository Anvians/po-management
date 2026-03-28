from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import httpx, os

from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductUpdate, ProductResponse, AIDescriptionRequest
from app.routers.auth import verify_token

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


@router.get("/", response_model=List[ProductResponse])
def list_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Product).offset(skip).limit(limit).all()


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token)
):
    existing = db.query(Product).filter(Product.sku == product.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists")
    
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    for field, value in product_update.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()


@router.post("/{product_id}/generate-description")
async def generate_ai_description(
    product_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_token)
):
    """Generate AI marketing description using Gemini API."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    description = await _call_gemini(product.name, product.category or "General")
    product.ai_description = description
    db.commit()
    db.refresh(product)
    return {"ai_description": description}


@router.post("/generate-description/preview")
async def preview_ai_description(req: AIDescriptionRequest):
    """Generate AI description without saving (preview mode)."""
    description = await _call_gemini(req.product_name, req.category or "General")
    return {"ai_description": description}


async def _call_gemini(product_name: str, category: str) -> str:
    """Call Gemini API to generate a 2-sentence marketing description."""
    prompt = (
        f"Write exactly 2 sentences of professional marketing copy for a product called "
        f"'{product_name}' in the '{category}' category. "
        f"Make it compelling, benefit-focused, and suitable for a B2B purchase order system. "
        f"Return only the 2 sentences, nothing else."
    )

    if not GEMINI_API_KEY:
        # Fallback: rule-based description when no API key configured
        return (
            f"The {product_name} is a premium {category.lower()} solution designed to streamline "
            f"your business operations with unmatched reliability and performance. "
            f"Trusted by industry leaders, it delivers exceptional value and seamlessly integrates "
            f"into your existing procurement workflow."
        )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
