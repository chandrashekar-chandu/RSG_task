"""
Comprehensive Automated Test Suite
==================================
Covers functional requirements, deterministic mathematical validation,
edge-case handling, SQL injection security guardrails, and API endpoints.
"""

import pytest
import pandas as pd
from fastapi.testclient import TestClient

from database import clean_sales_data, init_db, get_kpis, execute_query
from validator import validate_sql
from agent import SalesBIAssistant
from api import app


@pytest.fixture(scope="module")
def setup_db():
    """Ensures database is initialized before tests run."""
    conn = init_db()
    conn.close()
    return True


@pytest.fixture(scope="module")
def assistant(setup_db):
    """Provides an initialized instance of SalesBIAssistant."""
    return SalesBIAssistant()


@pytest.fixture(scope="module")
def api_client(setup_db):
    """Provides a TestClient for testing FastAPI REST endpoints."""
    return TestClient(app)


# -------------------------------------------------------------
# Test Group 1: Data Management & Imputation
# -------------------------------------------------------------

def test_data_cleaning_and_imputation():
    """
    Verifies that:
    1. Total records equal 51.
    2. Missing unit price in row TXN0051 (Laptop Stand) is imputed to 1200.0.
    3. Dates are standardized from DD-MM-YYYY to ISO YYYY-MM-DD.
    4. Gross and Net revenues are pre-calculated accurately.
    """
    df = clean_sales_data()
    assert len(df) == 51, f"Expected 51 records, found {len(df)}"

    # Check imputation for Laptop Stand
    txn_51 = df[df["transaction_id"] == "TXN0051"]
    assert len(txn_51) == 1
    assert txn_51.iloc[0]["unit_price"] == 1200.0, "Missing unit_price for Laptop Stand was not imputed to 1200.0"
    assert txn_51.iloc[0]["net_revenue"] == 5 * 1200.0, "Net revenue calculation for TXN0051 is incorrect"

    # Check date conversion to ISO format (YYYY-MM-DD)
    sample_date = df.iloc[0]["order_date"]
    assert len(sample_date) == 10 and sample_date.startswith("2026-"), f"Date not in YYYY-MM-DD format: {sample_date}"


# -------------------------------------------------------------
# Test Group 2: The 5 Benchmark Assessment Questions
# -------------------------------------------------------------

def test_question_1_total_revenue(assistant):
    """Validates calculation for Question 1: What is the total revenue?"""
    res = assistant.process_query("What is the total revenue?")
    assert res["status"] == "success"
    assert len(res["data"]) == 1
    data = res["data"][0]

    assert data["total_net_revenue"] == 1445200.0, f"Expected 1445200.0, got {data['total_net_revenue']}"
    assert data["total_gross_revenue"] == 1449700.0, f"Expected 1449700.0, got {data['total_gross_revenue']}"
    assert data["total_discounts"] == 4500.0, f"Expected 4500.0, got {data['total_discounts']}"
    assert data["completed_transactions"] == 50, f"Expected 50 completed orders, got {data['completed_transactions']}"


def test_question_2_highest_revenue_product(assistant):
    """Validates calculation for Question 2: Which product generated the highest revenue?"""
    res = assistant.process_query("Which product generated the highest revenue?")
    assert res["status"] == "success"
    assert len(res["data"]) >= 7  # 7 unique products

    top_row = res["data"][0]
    assert top_row["product"] == "Monitor", f"Expected Monitor as top product, got {top_row['product']}"
    assert top_row["total_net_revenue"] == 473000.0, f"Expected Monitor revenue 473000.0, got {top_row['total_net_revenue']}"
    assert top_row["units_sold"] == 50, f"Expected 50 units sold for Monitor, got {top_row['units_sold']}"


def test_question_3_monthly_revenue_trend(assistant):
    """Validates calculation for Question 3: What is the monthly revenue trend?"""
    res = assistant.process_query("What is the monthly revenue trend?")
    assert res["status"] == "success"
    assert len(res["data"]) == 6, f"Expected 6 monthly records, got {len(res['data'])}"

    monthly_dict = {r["month"]: r["net_revenue"] for r in res["data"]}
    expected_months = {
        "2026-01": 210250.0,
        "2026-02": 234600.0,
        "2026-03": 223900.0,
        "2026-04": 240700.0,
        "2026-05": 318500.0,
        "2026-06": 217250.0
    }
    assert monthly_dict == expected_months, f"Monthly mismatch. Got {monthly_dict}"


def test_question_4_highest_sales_region(assistant):
    """Validates calculation for Question 4: Which region generated the highest sales?"""
    res = assistant.process_query("Which region generated the highest sales?")
    assert res["status"] == "success"
    assert len(res["data"]) == 4, f"Expected 4 regions, got {len(res['data'])}"

    top_region = res["data"][0]
    assert top_region["region"] == "South", f"Expected South as top region, got {top_region['region']}"
    assert top_region["total_net_revenue"] == 411200.0, f"Expected South revenue 411200.0, got {top_region['total_net_revenue']}"
    assert top_region["revenue_share_pct"] == 28.45, f"Expected 28.45% share, got {top_region['revenue_share_pct']}"


def test_question_5_month_over_month_change(assistant):
    """Validates calculation for Question 5: How did revenue change between two months?"""
    res = assistant.process_query("How did revenue change between two months?")
    assert res["status"] == "success"
    assert len(res["data"]) == 6

    # Verify peak increase occurred in May 2026 (2026-05 vs 2026-04)
    may_row = next(r for r in res["data"] if r["month"] == "2026-05")
    assert may_row["absolute_change"] == 77800.0, f"Expected May increase of +77800.0, got {may_row['absolute_change']}"
    assert may_row["percentage_change"] == 32.32, f"Expected May percentage gain of 32.32%, got {may_row['percentage_change']}"


# -------------------------------------------------------------
# Test Group 3: Edge Cases (Returned status & Zero quantity)
# -------------------------------------------------------------

def test_edge_case_returned_order_excluded():
    """Verifies that Returned order TXN0033 is excluded from revenue calculations."""
    df, _ = execute_query("SELECT COUNT(*) AS returned_count FROM sales_transactions WHERE status = 'Returned';")
    assert df.iloc[0]["returned_count"] == 1, "Expected exactly 1 returned transaction"

    df_rev, _ = execute_query("SELECT SUM(net_revenue) AS completed_rev FROM sales_transactions WHERE status = 'Completed';")
    df_all, _ = execute_query("SELECT SUM(net_revenue) AS total_all FROM sales_transactions;")
    
    # 2 units * 9500 = 19000 returned value
    assert df_all.iloc[0]["total_all"] - df_rev.iloc[0]["completed_rev"] == 19000.0


def test_edge_case_zero_quantity():
    """Verifies that TXN0034 with quantity = 0 does not trigger exceptions or distort metrics."""
    df, _ = execute_query("SELECT net_revenue, gross_revenue FROM sales_transactions WHERE transaction_id = 'TXN0034';")
    assert df.iloc[0]["net_revenue"] == 0.0
    assert df.iloc[0]["gross_revenue"] == 0.0


# -------------------------------------------------------------
# Test Group 4: SQL Security Guardrails & Injection Defense
# -------------------------------------------------------------

def test_guardrail_blocks_drop_table(assistant):
    """Tests that destructive DROP TABLE commands are rejected immediately."""
    res = assistant.process_query("DROP TABLE sales_transactions;")
    assert res["status"] == "security_violation"
    assert "Security Violation" in res["answer"]


def test_guardrail_blocks_delete_and_update(assistant):
    """Tests that DELETE and UPDATE statements are blocked."""
    is_valid, err, _ = validate_sql("DELETE FROM sales_transactions WHERE quantity = 0;")
    assert not is_valid
    assert "Security Violation" in err

    is_valid, err, _ = validate_sql("UPDATE sales_transactions SET net_revenue = 999999;")
    assert not is_valid
    assert "Security Violation" in err


def test_guardrail_blocks_multistatement_injection(assistant):
    """Tests that stacked multi-statement injection via semicolons is blocked."""
    malicious = "SELECT * FROM sales_transactions; DROP TABLE sales_transactions;"
    is_valid, err, _ = validate_sql(malicious)
    assert not is_valid
    assert "Multi-statement" in err


def test_guardrail_blocks_unauthorized_table(assistant):
    """Tests that querying unauthorized system tables like sqlite_master is blocked."""
    is_valid, err, _ = validate_sql("SELECT name FROM sqlite_master WHERE type='table';")
    assert not is_valid
    assert "Access Denied" in err


# -------------------------------------------------------------
# Test Group 5: Out of Scope & Empty Inputs
# -------------------------------------------------------------

def test_out_of_scope_query_handling(assistant):
    """Tests that irrelevant questions return a polite, structured unsupported response."""
    res = assistant.process_query("What is the current temperature in Paris?")
    assert res["status"] == "unsupported"
    assert "outside the scope" in res["answer"]


def test_empty_query_handling(assistant):
    """Tests that blank/whitespace inputs return an appropriate prompt."""
    res = assistant.process_query("   ")
    assert res["status"] == "error"
    assert "Please enter a question" in res["answer"]


# -------------------------------------------------------------
# Test Group 6: FastAPI Endpoints Verification
# -------------------------------------------------------------

def test_fastapi_health_endpoint(api_client):
    """Verifies GET /api/health endpoint returns 200 OK and valid DB status."""
    response = api_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["total_records"] == 51


def test_fastapi_summary_endpoint(api_client):
    """Verifies GET /api/summary returns executive metrics."""
    response = api_client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_net_revenue"] == 1445200.0
    assert data["top_product"] == "Monitor"
    assert data["top_region"] == "South"


def test_fastapi_query_endpoint(api_client):
    """Verifies POST /api/query processes requests and returns structured schema."""
    response = api_client.post("/api/query", json={"question": "What is the total revenue?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "₹1,445,200.00" in data["answer"]
    assert "SELECT" in data["sql_query"]
    assert len(data["data"]) == 1
