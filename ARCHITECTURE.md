# Architecture & Design Document: Mini AI Business Intelligence Assistant

This document details the architectural decisions, component design, data flow, security model, and interview-aligned concepts implemented in the **Mini AI Business Intelligence Assistant**.

---

## 1. Architectural Paradigm: Vectorless RAG

### Traditional RAG vs. Vectorless RAG for Structured Data

| Dimension | Traditional Vector RAG (Embeddings + Vector DB) | Vectorless RAG (Schema + Text-to-SQL) [Implemented] |
| :--- | :--- | :--- |
| **Core Storage** | Vector Database (Chroma, Pinecone, FAISS) storing document embeddings. | Relational Database (SQLite) storing structured transactional records. |
| **Retrieval Mechanism** | Cosine similarity / Semantic distance search across text chunks. | Deterministic relational query execution (`SELECT`, `GROUP BY`, `SUM`, `WHERE`). |
| **Aggregation Capability** | **Extremely Poor**: Cannot compute mathematical sums, averages, or medians over hundreds of rows without hallucinations. | **Exact & Verifiable**: Computes mathematical aggregations deterministically in milliseconds. |
| **Hallucination Risk** | High for numeric calculations and dates. | Zero arithmetic hallucination (arithmetic is delegated to SQLite). |
| **Explainability** | Black-box embedding scores. | Full transparency via inspectable, human-readable SQL queries. |
| **Safety & Control** | Hard to restrict unauthorized numeric aggregation. | Strict AST and keyword guardrails enforce read-only execution. |

---

## 2. End-to-End Component Architecture

```mermaid
graph TD
    subgraph Client Layer
        WebUI["🖥️ Streamlit Interactive UI (app.py)"]
        ExternalAPI["🌐 REST Clients / cURL"]
    end

    subgraph Service Layer
        FastAPIService["⚡ FastAPI REST Gateway (api.py)"]
        Endpoints["Endpoints:\n- POST /api/query\n- GET /api/health\n- GET /api/summary\n- GET /api/schema"]
    end

    subgraph Core Intelligence Layer
        AgentEngine["🧠 Vectorless RAG Agent (agent.py)"]
        IntentRouter["🔀 Intent Router & Text-to-SQL Translator"]
        LLMModule["🤖 LLM Fallback (OpenAI/Gemini/Groq SDK)"]
        NarrativeSynthesizer["✍️ Business Narrative Synthesizer"]
    end

    subgraph Security & Governance Layer
        GuardrailValidator["🛡️ SQL Security Validator (validator.py)"]
        WhitelistChecker["📋 Table & Column Whitelist"]
        ASTParser["🚫 Read-Only & Injection Prevention"]
    end

    subgraph Data & Storage Layer
        DBEngine["🗄️ Embedded SQLite Engine (sales_bi.db)"]
        ETLPipeline["⚙️ ETL & Data Cleaning Pipeline (database.py)"]
        CSVSource["📄 Sales Transactions CSV (51 records)"]
    end

    WebUI --> FastAPIService
    ExternalAPI --> FastAPIService
    FastAPIService --> Endpoints
    Endpoints --> AgentEngine
    
    AgentEngine --> IntentRouter
    IntentRouter -.->|Optional API Key| LLMModule
    IntentRouter --> GuardrailValidator
    
    GuardrailValidator --> ASTParser
    ASTParser --> WhitelistChecker
    WhitelistChecker -->|Safe SQL| DBEngine
    
    CSVSource --> ETLPipeline
    ETLPipeline -->|Cleaned, Imputed & Indexed Data| DBEngine
    
    DBEngine -->|Query Results DataFrame| NarrativeSynthesizer
    NarrativeSynthesizer --> FastAPIService
    FastAPIService --> WebUI
```

---

## 3. Data Ingestion & ETL Flow

```mermaid
sequenceDiagram
    autonumber
    participant CSV as Raw CSV File
    participant ETL as ETL Pipeline (database.py)
    participant SQLite as SQLite Database (sales_bi.db)

    ETL->>CSV: Load raw transactions (51 rows, 10 columns)
    ETL->>ETL: 1. Trim column whitespace
    ETL->>ETL: 2. Check for missing values (Row TXN0051 Unit_price is NULL)
    ETL->>ETL: 3. Impute Laptop Stand unit_price = 1200.0 (Product Median)
    ETL->>ETL: 4. Standardize dates from DD-MM-YYYY to ISO YYYY-MM-DD
    ETL->>ETL: 5. Calculate Gross_revenue = Quantity * Unit_price
    ETL->>ETL: 6. Calculate Net_revenue = Gross_revenue - Discount_amount
    ETL->>SQLite: Create schema `sales_transactions`
    ETL->>SQLite: Insert cleaned records
    ETL->>SQLite: Build B-Tree indexes on order_date, product, region, status
```

---

## 4. Query Execution Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as Business User
    participant UI as Streamlit / API
    participant Agent as Vectorless RAG Agent
    participant Validator as Security Guardrail
    participant DB as SQLite DB
    participant Synth as Synthesizer

    User->>UI: "Which product generated the highest revenue?"
    UI->>Agent: process_query(question)
    Agent->>Agent: Resolve intent to SQL query
    Agent->>Validator: validate_sql(generated_sql)
    
    alt Validation Fails (e.g. DROP TABLE or Invalid Syntax)
        Validator-->>Agent: (is_valid=False, error_msg)
        Agent-->>UI: Return security alert / error
    else Validation Passes
        Validator-->>Agent: (is_valid=True, sanitized_sql)
        Agent->>DB: execute_query(sanitized_sql)
        DB-->>Agent: DataFrame (rows, columns)
        Agent->>Synth: Synthesize answer with figures & comparisons
        Synth-->>Agent: Formatted text response
        Agent-->>UI: {question, status, answer, sql_query, data, latency_ms}
        UI-->>User: Display KPI card, Answer, SQL block, Chart, Table
    end
```

---

## 5. Security & Safety Architecture

To satisfy strict enterprise evaluation criteria, the security validator enforces the following controls:

1. **Strict Read-Only Enforcement**:
   - Queries must strictly begin with `SELECT` or `WITH`.
   - Modifying and administrative statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `EXEC`, `PRAGMA`, `ATTACH`, `DETACH`) are blocked using regular expressions.
2. **Multi-Statement Injection Prevention**:
   - Chained SQL queries using `;` (e.g. `SELECT 1; DROP TABLE sales;`) are rejected before reaching the SQLite cursor.
3. **Table & Schema Whitelisting**:
   - Queries are checked against `ALLOWED_TABLES = {"sales_transactions"}`. Access to system tables (`sqlite_master`, `sqlite_temp_master`) is blocked.
4. **Out-of-Scope Safeguards**:
   - Queries unrelated to sales metrics (e.g., weather, executive salaries, trivia) trigger an immediate, graceful `unsupported` response rather than executing hallucinated queries.

---

## 6. Technical Stack Summary

* **Language**: Python 3.10
* **Storage & Relational Engine**: SQLite 3 (zero external dependencies, ACID compliant, embedded)
* **Data Processing**: Pandas 2.3, NumPy
* **API Framework**: FastAPI 0.162 + Uvicorn + Pydantic v2
* **Frontend**: Streamlit 1.55 + Altair Interactive Charts
* **Test Framework**: Pytest 9.2
