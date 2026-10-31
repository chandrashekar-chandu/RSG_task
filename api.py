"""
FastAPI REST API Service
========================
Provides structured REST endpoints for the Sales BI Assistant:
- POST /api/query: Natural language query processing & Vectorless RAG
- GET  /api/health: Service and database health check
- GET  /api/summary: High-level executive KPIs
- GET  /api/schema: Table schema and analytical metadata
"""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import SalesBIAssistant
from database import get_kpis, get_schema_info

app = FastAPI(
    title="Mini AI Business Intelligence Assistant API",
    description="Vectorless RAG Sales BI Backend API built for the RSG Research GET Challenge.",
    version="1.0.0"
)

# Enable CORS for web frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistant = SalesBIAssistant()


# Pydantic Schemas
class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        description="Natural language question about sales transactions",
        json_schema_extra={"example": "What is the total revenue?"}
    )


class QueryResponse(BaseModel):
    question: str
    status: str
    answer: str
    sql_query: str
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    latency_ms: float


@app.get("/", tags=["General"])
def root():
    """Welcome endpoint with links to interactive docs."""
    return {
        "message": "Welcome to the Mini AI Business Intelligence Assistant API",
        "documentation": "/docs",
        "health_check": "/api/health",
        "sample_query_endpoint": "/api/query"
    }


@app.get("/api/health", tags=["Monitoring"])
def health_check():
    """Returns system status, database connectivity, and total records count."""
    try:
        kpis = get_kpis()
        return {
            "status": "healthy",
            "database": "connected",
            "total_records": kpis["total_records"],
            "completed_orders": kpis["completed_orders"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity failed: {str(e)}"
        )


@app.get("/api/summary", tags=["Analytics"])
def get_executive_summary():
    """Returns top-level executive KPIs (Revenue, Top Product, Peak Month)."""
    try:
        return get_kpis()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute executive summary: {str(e)}"
        )


@app.get("/api/schema", tags=["Metadata"])
def get_database_schema():
    """Returns database schema information, columns, and business rules."""
    return get_schema_info()


@app.post("/api/query", response_model=QueryResponse, tags=["AI Assistant"])
def query_sales_assistant(payload: QueryRequest):
    """
    Accepts a natural language business question, runs the Vectorless RAG pipeline,
    and returns a structured JSON answer backed by executed SQL.
    """
    if not payload.question or not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'question' field cannot be blank."
        )

    response = assistant.process_query(payload.question)
    return response


if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI Server on http://127.0.0.1:8000 ...")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
