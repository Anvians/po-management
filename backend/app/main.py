from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import vendors, products, purchase_orders, auth
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PO Management System",
    description="Purchase Order Management System with AI Integration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(vendors.router, prefix="/api/vendors", tags=["Vendors"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(purchase_orders.router, prefix="/api/purchase-orders", tags=["Purchase Orders"])

@app.get("/")
def root():
    return {"message": "PO Management System API", "status": "running", "docs": "/docs"}
