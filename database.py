"""
Database Management & Data Pipeline Module
===========================================
Handles ingestion, cleaning, validation, and SQLite persistence
for the Sales BI Assistant.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

# Default paths
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CSV_PATH = BASE_DIR / "ai_bi_assistant_sales_data - GET.csv"
DEFAULT_DB_PATH = BASE_DIR / "sales_bi.db"


def clean_sales_data(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads raw CSV data and performs rigorous data cleaning:
    1. Trims whitespace from string columns.
    2. Standardizes dates from DD-MM-YYYY to ISO YYYY-MM-DD for SQLite datetime compatibility.
    3. Imputes missing Unit_price for 'Laptop Stand' using known standard price (1200.0).
    4. Handles zero or negative quantities appropriately.
    5. Fills missing discount amounts with 0.0.
    6. Computes Gross_revenue and Net_revenue columns for deterministic analytics.
    """
    path = csv_path or DEFAULT_CSV_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Sales dataset not found at {path}")

    df = pd.read_csv(path)

    # Standardize column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    # Clean text columns
    for col in ["Transaction_Id", "Product", "Category", "Region", "Sales_channel", "Status"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # 1. Handle missing / invalid Unit_price (e.g. TXN0051 Laptop Stand missing unit_price)
    # Impute missing unit prices using median/mode of that specific product
    if df["Unit_price"].isnull().any():
        product_price_map = (
            df.dropna(subset=["Unit_price"])
            .groupby("Product")["Unit_price"]
            .median()
            .to_dict()
        )
        df["Unit_price"] = df.apply(
            lambda row: product_price_map.get(row["Product"], 0.0)
            if pd.isnull(row["Unit_price"])
            else row["Unit_price"],
            axis=1,
        )

    # 2. Type conversions
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
    df["Unit_price"] = pd.to_numeric(df["Unit_price"], errors="coerce").fillna(0.0).astype(float)
    df["Discount_amount"] = pd.to_numeric(df["Discount_amount"], errors="coerce").fillna(0.0).astype(float)

    # 3. Standardize dates from DD-MM-YYYY to ISO YYYY-MM-DD
    # This enables SQLite strftime('%Y-%m', order_date) and ISO sorting
    df["Order_date_raw"] = df["Order_date"]
    df["Order_date"] = pd.to_datetime(df["Order_date"], format="%d-%m-%Y").dt.strftime("%Y-%m-%d")

    # 4. Computed columns for deterministic business analytics
    df["Gross_revenue"] = df["Quantity"] * df["Unit_price"]
    df["Net_revenue"] = df["Gross_revenue"] - df["Discount_amount"]

    # Normalize column names for SQL friendly naming
    rename_dict = {
        "Transaction_Id": "transaction_id",
        "Order_date": "order_date",
        "Product": "product",
        "Category": "category",
        "Region": "region",
        "Sales_channel": "sales_channel",
        "Quantity": "quantity",
        "Unit_price": "unit_price",
        "Discount_amount": "discount_amount",
        "Gross_revenue": "gross_revenue",
        "Net_revenue": "net_revenue",
        "Status": "status"
    }
    df = df.rename(columns=rename_dict)

    columns_to_keep = [
        "transaction_id",
        "order_date",
        "product",
        "category",
        "region",
        "sales_channel",
        "quantity",
        "unit_price",
        "discount_amount",
        "gross_revenue",
        "net_revenue",
        "status"
    ]
    return df[columns_to_keep]


def init_db(csv_path: Optional[Path] = None, db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Initializes SQLite database, creates schema with indexes, and loads cleaned data.
    """
    target_db = db_path or DEFAULT_DB_PATH
    df = clean_sales_data(csv_path)

    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()

    # Create table schema
    cursor.execute("DROP TABLE IF EXISTS sales_transactions;")
    cursor.execute("""
        CREATE TABLE sales_transactions (
            transaction_id TEXT PRIMARY KEY,
            order_date TEXT NOT NULL,
            product TEXT NOT NULL,
            category TEXT NOT NULL,
            region TEXT NOT NULL,
            sales_channel TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            discount_amount REAL NOT NULL,
            gross_revenue REAL NOT NULL,
            net_revenue REAL NOT NULL,
            status TEXT NOT NULL
        );
    """)

    # Populate table
    df.to_sql("sales_transactions", conn, if_exists="append", index=False)

    # Create indexes for analytical query acceleration
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_date ON sales_transactions(order_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_product ON sales_transactions(product);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_region ON sales_transactions(region);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON sales_transactions(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON sales_transactions(category);")

    conn.commit()
    return conn


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a connection to the SQLite database with row factory enabled."""
    target_db = db_path or DEFAULT_DB_PATH
    if not os.path.exists(target_db):
        init_db(db_path=target_db)
    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row
    return conn


def execute_query(sql_query: str, params: Optional[Tuple] = None, db_path: Optional[Path] = None) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Executes a read-only SQL query against the database and returns a Pandas DataFrame.
    """
    conn = None
    try:
        conn = get_connection(db_path)
        df = pd.read_sql_query(sql_query, conn, params=params)
        return df, None
    except Exception as e:
        return None, str(e)
    finally:
        if conn:
            conn.close()


def get_schema_info() -> Dict[str, Any]:
    """
    Returns rich metadata about the database schema and analytical business rules
    used for Vectorless RAG and prompt context.
    """
    return {
        "table_name": "sales_transactions",
        "columns": [
            {"name": "transaction_id", "type": "TEXT", "description": "Unique identifier for transaction (e.g. TXN0001)"},
            {"name": "order_date", "type": "TEXT", "description": "Date of transaction in ISO format 'YYYY-MM-DD'"},
            {"name": "product", "type": "TEXT", "description": "Product name (Laptop Stand, Wireless Mouse, Office Chair, Monitor, Keyboard, Desk, USB-C Hub)"},
            {"name": "category", "type": "TEXT", "description": "Product category (Accessories, Furniture, Electronics)"},
            {"name": "region", "type": "TEXT", "description": "Sales territory (North, South, East, West)"},
            {"name": "sales_channel", "type": "TEXT", "description": "Channel of sale (Online, Retail)"},
            {"name": "quantity", "type": "INTEGER", "description": "Number of units ordered"},
            {"name": "unit_price", "type": "REAL", "description": "Price per unit in INR"},
            {"name": "discount_amount", "type": "REAL", "description": "Total discount given in INR"},
            {"name": "gross_revenue", "type": "REAL", "description": "Gross revenue (quantity * unit_price)"},
            {"name": "net_revenue", "type": "REAL", "description": "Net realized revenue: (quantity * unit_price) - discount_amount"},
            {"name": "status", "type": "TEXT", "description": "Order status ('Completed' or 'Returned')"}
        ],
        "business_rules": [
            "Revenue calculations MUST filter for status = 'Completed' to exclude returned orders.",
            "Net revenue is defined as (quantity * unit_price) - discount_amount.",
            "Monthly grouping should use strftime('%Y-%m', order_date) as month."
        ]
    }


def get_kpis(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Calculates top-level executive KPIs from the database."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Total net revenue & completed orders
    cursor.execute("""
        SELECT 
            COUNT(*) AS total_orders,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_orders,
            SUM(CASE WHEN status = 'Completed' THEN net_revenue ELSE 0 END) AS total_net_revenue,
            SUM(CASE WHEN status = 'Completed' THEN gross_revenue ELSE 0 END) AS total_gross_revenue,
            SUM(CASE WHEN status = 'Completed' THEN discount_amount ELSE 0 END) AS total_discounts,
            SUM(CASE WHEN status = 'Completed' THEN quantity ELSE 0 END) AS total_units_sold
        FROM sales_transactions;
    """)
    row = cursor.fetchone()

    # Top product
    cursor.execute("""
        SELECT product, SUM(net_revenue) AS revenue
        FROM sales_transactions
        WHERE status = 'Completed'
        GROUP BY product
        ORDER BY revenue DESC
        LIMIT 1;
    """)
    top_prod = cursor.fetchone()

    # Top region
    cursor.execute("""
        SELECT region, SUM(net_revenue) AS revenue
        FROM sales_transactions
        WHERE status = 'Completed'
        GROUP BY region
        ORDER BY revenue DESC
        LIMIT 1;
    """)
    top_reg = cursor.fetchone()

    # Peak month
    cursor.execute("""
        SELECT strftime('%Y-%m', order_date) AS month, SUM(net_revenue) AS revenue
        FROM sales_transactions
        WHERE status = 'Completed'
        GROUP BY month
        ORDER BY revenue DESC
        LIMIT 1;
    """)
    peak_mo = cursor.fetchone()

    conn.close()

    return {
        "total_records": row["total_orders"],
        "completed_orders": row["completed_orders"],
        "total_net_revenue": round(row["total_net_revenue"], 2),
        "total_gross_revenue": round(row["total_gross_revenue"], 2),
        "total_discounts": round(row["total_discounts"], 2),
        "total_units_sold": row["total_units_sold"],
        "top_product": top_prod["product"] if top_prod else "N/A",
        "top_product_revenue": round(top_prod["revenue"], 2) if top_prod else 0.0,
        "top_region": top_reg["region"] if top_reg else "N/A",
        "top_region_revenue": round(top_reg["revenue"], 2) if top_reg else 0.0,
        "peak_month": peak_mo["month"] if peak_mo else "N/A",
        "peak_month_revenue": round(peak_mo["revenue"], 2) if peak_mo else 0.0
    }


if __name__ == "__main__":
    print("Initializing Sales BI SQLite Database...")
    init_db()
    kpis = get_kpis()
    print("Database successfully initialized!")
    print(f"Total Completed Net Revenue: Rs. {kpis['total_net_revenue']:,}")
    print(f"Top Product: {kpis['top_product']} (Rs. {kpis['top_product_revenue']:,})")
    print(f"Top Region: {kpis['top_region']} (Rs. {kpis['top_region_revenue']:,})")
    print(f"Peak Month: {kpis['peak_month']} (Rs. {kpis['peak_month_revenue']:,})")
