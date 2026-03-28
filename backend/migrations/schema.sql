-- ============================================================
-- PO Management System - Database Schema + Seed Data
-- ============================================================

-- NOTE:
-- Database is automatically created via POSTGRES_DB
-- So no CREATE DATABASE or \c needed here

-- ENUM for PO status
DO $$ BEGIN
    CREATE TYPE postatus AS ENUM ('draft', 'pending', 'approved', 'rejected', 'completed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ── Vendors ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vendors (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    contact     VARCHAR(255) NOT NULL,
    email       VARCHAR(255) UNIQUE NOT NULL,
    phone       VARCHAR(20),
    rating      FLOAT DEFAULT 0.0 CHECK (rating >= 0 AND rating <= 5),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ
);

-- ── Products ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(255) NOT NULL,
    sku            VARCHAR(100) UNIQUE NOT NULL,
    category       VARCHAR(100),
    unit_price     FLOAT NOT NULL CHECK (unit_price > 0),
    stock_level    INTEGER DEFAULT 0 CHECK (stock_level >= 0),
    description    TEXT,
    ai_description TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ
);

-- ── Purchase Orders ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS purchase_orders (
    id           SERIAL PRIMARY KEY,
    reference_no VARCHAR(50) UNIQUE NOT NULL,
    vendor_id    INTEGER NOT NULL REFERENCES vendors(id),
    subtotal     FLOAT DEFAULT 0.0,
    tax_amount   FLOAT DEFAULT 0.0,
    total_amount FLOAT DEFAULT 0.0,
    status       postatus DEFAULT 'draft',
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ
);

-- ── Purchase Order Items ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS purchase_order_items (
    id                  SERIAL PRIMARY KEY,
    purchase_order_id   INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id          INTEGER NOT NULL REFERENCES products(id),
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    unit_price          FLOAT NOT NULL,
    line_total          FLOAT NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_po_vendor_id ON purchase_orders(vendor_id);
CREATE INDEX IF NOT EXISTS idx_po_status ON purchase_orders(status);
CREATE INDEX IF NOT EXISTS idx_poi_po_id ON purchase_order_items(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_poi_product_id ON purchase_order_items(product_id);

-- ── Seed Data ──────────────────────────────────────────────────────────────

INSERT INTO vendors (name, contact, email, phone, rating) VALUES
    ('TechSupply Co.',       'Rahul Sharma',   'rahul@techsupply.in',    '+91-9876543210', 4.5),
    ('GlobalParts Ltd.',     'Priya Mehta',    'priya@globalparts.com',  '+91-9812345678', 4.2),
    ('SwiftLogistics Inc.',  'Arjun Nair',     'arjun@swiftlog.in',      '+91-9823456789', 3.8),
    ('PrimeMaterials Pvt.',  'Sunita Verma',   'sunita@primemats.co.in', '+91-9834567890', 4.7)
ON CONFLICT (email) DO NOTHING;

INSERT INTO products (name, sku, category, unit_price, stock_level, description) VALUES
    ('Dell Laptop 15"',      'DELL-LAP-001', 'Electronics',  65000.00, 50,  'High-performance business laptop'),
    ('Wireless Mouse',       'MICE-WL-002',  'Peripherals',   1200.00, 200, 'Ergonomic wireless mouse'),
    ('USB-C Hub 7-port',     'USBC-HUB-003', 'Peripherals',   2500.00, 150, '7-in-1 USB-C hub'),
    ('Office Chair Pro',     'CHAIR-OP-004', 'Furniture',    15000.00, 30,  'Ergonomic office chair'),
    ('Standing Desk',        'DESK-ST-005',  'Furniture',    25000.00, 20,  'Electric height-adjustable desk'),
    ('A4 Paper Ream (500)',  'PAPER-A4-006', 'Stationery',     350.00, 500, 'Premium A4 paper 80gsm'),
    ('Mechanical Keyboard',  'KB-MECH-007',  'Peripherals',   4500.00, 100, 'RGB mechanical keyboard'),
    ('27" Monitor 4K',       'MON-4K-008',   'Electronics',  35000.00, 40,  '4K IPS display monitor')
ON CONFLICT (sku) DO NOTHING;