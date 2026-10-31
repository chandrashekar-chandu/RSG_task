# AI Usage, Engineering Reflection & Interview Preparation Guide

**Candidate Assessment Submission**: Mini AI Business Intelligence Assistant  
**Role**: Graduate Engineer Trainee (Python with Generative AI)  
**Company**: RSG Research Private Limited  
**Institution**: RGUKT-Basar  

---

## 1. Which AI Tools Were Used

During the design and implementation of this project, the following AI tools and coding assistants were leveraged:

1. **Google Gemini (Advanced Agentic Assistant)**:
   - Used for end-to-end task breakdown, architectural reasoning, automated test suite generation, and designing the **Vectorless RAG** pipeline.
2. **Claude 3.5 Sonnet / ChatGPT**:
   - Used for brainstorming edge cases in transactional sales datasets (imputation strategies for missing values, date format standardizations, returned order accounting).
3. **GitHub Copilot / Cursor**:
   - Used for accelerating repetitive Python boilerplates (Pydantic schema definitions, Streamlit Altair chart specifications, and FastAPI routing).

---

## 2. How AI Was Used During Development

AI was utilized as a **collaborative pair programmer and architectural advisor**, following an iterative development lifecycle:

1. **Schema & Data Modeling**:
   - Analyzed the supplied CSV (`ai_bi_assistant_sales_data - GET.csv`) using automated python profiling scripts to uncover anomalies:
     - Identification of blank `Unit_price` on `TXN0051`.
     - Detection of non-standard date format (`DD-MM-YYYY`).
     - Identification of the `Returned` order status on `TXN0033`.
   - Used AI to design the data transformation pipeline: converting dates to ISO `YYYY-MM-DD` so SQLite `strftime()` functions operate natively.
2. **Vectorless RAG vs. Vector RAG Decision**:
   - Evaluated whether to use vector embeddings (Chroma/FAISS) vs. relational SQL generation (Vectorless RAG). AI assisted in analyzing why vector embeddings produce hallucinated aggregations on tabular numeric data, proving that **Text-to-SQL + SQLite** is mathematically superior and deterministic.
3. **Security Guardrail Design**:
   - Collaborated with AI to write regular expressions and AST parsers in `validator.py` that reject all destructive keywords (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `ATTACH`) and block stacked SQL injection attacks.
4. **Test-Driven Verification**:
   - Generated 17 automated unit and integration tests across data ingestion, the 5 core challenge questions, edge cases, SQL injections, and API responses.

---

## 3. Which Problems Were Encountered

During the 3–4 hour development window, four key technical hurdles were encountered:

1. **Missing Value in Transaction Data**:
   - Row 51 (`TXN0051`) had an empty string / `NaN` for `Unit_price` for "Laptop Stand". If left unhandled, it caused SQLite queries to return `NULL` for revenue totals.
2. **SQLite Date Incompatibility**:
   - The CSV provided dates in `DD-MM-YYYY` format (e.g. `03-01-2026`). In SQLite, running `strftime('%Y-%m', order_date)` on `DD-MM-YYYY` fails because SQLite datetime functions expect ISO-8601 (`YYYY-MM-DD`).
3. **Accounting for Returned Transactions**:
   - Transaction `TXN0033` has a status of `Returned` (Monitor, 2 units @ ₹9,500 = ₹19,000). Calculating revenue blindly (`SUM(quantity * unit_price)`) produces **₹1,464,200**, inflating the real revenue.
4. **Windows Console Unicode Encoding Bug**:
   - When printing the Rupee symbol (`₹` / `\u20b9`) in Windows PowerShell / Command Prompt, Python threw `UnicodeEncodeError: 'charmap' codec can't encode character '\u20b9'`.
5. **SQL Injection Vulnerabilities in Text-to-SQL**:
   - Free-form text-to-SQL agents can be prompted to generate `DROP TABLE sales_transactions;` or chained statements (`SELECT ...; DELETE FROM ...;`).

---

## 4. How They Were Debugged and Resolved

| Issue | Debugging Method | Final Resolution |
| :--- | :--- | :--- |
| **Missing Price on Laptop Stand** | Inspected all other entries for "Laptop Stand" in the dataset. | Implemented automated product-level imputation: `Unit_price = 1200.0`. |
| **Date Parsing in SQLite** | Ran test query `SELECT strftime('%Y-%m', order_date)`; observed null/distorted output. | In `database.py`, used `pd.to_datetime(df['Order_date'], format='%d-%m-%Y').dt.strftime('%Y-%m-%d')` before writing to SQLite. |
| **Returned Order Distortion** | Reconciled transaction statuses; isolated `Status == 'Returned'`. | Added strict filtering `WHERE status = 'Completed'` to all revenue aggregations, yielding the true net revenue of **₹1,445,200.00**. |
| **Windows Console Unicode Crash** | Inspected exception stack trace pointing to `cp1252.py`. | Added `sys.stdout.reconfigure(encoding='utf-8')` and `sys.stderr.reconfigure(encoding='utf-8')` to ensure safe terminal output. |
| **Destructive SQL Risk** | Tested malicious inputs like `DROP TABLE sales;` in `agent.py`. | Created `validator.py` with multi-statement detection, `SELECT`/`WITH` enforcement, and keyword blacklists. |

---

## 5. What Would Be Improved with Another Day of Work

If given an additional 24 hours to scale this application into a production enterprise BI assistant:

1. **Conversational Memory & Multi-Turn Context**:
   - Implement an agentic state graph (using **LangGraph**) to maintain conversation context (e.g., User asks: *"Which product generated the highest revenue?"* followed by *"What about its sales in the North region?"*).
2. **Semantic Caching with Redis**:
   - Cache frequent query results and SQL translations using Redis to reduce latency from ~20ms to under 2ms.
3. **Automated Visualization Recommendation (Agentic Viz)**:
   - Use an LLM tool to automatically decide whether the result is best rendered as a Bar Chart, Multi-Line Trend, Donut Chart, or Pivot Table based on data cardinality.
4. **Multi-Table Relational Schema & Foreign Keys**:
   - Normalize the schema into 3 tables: `orders`, `products`, and `customers`/`regions` with foreign keys, simulating a true data warehouse (Star Schema).
5. **Speech-to-Text & Voice Querying**:
   - Integrate OpenAI Whisper or Web Speech API for voice-activated BI queries on executive mobile dashboards.

---

# 🎓 Technical Interview Preparation Sheet

This section covers the core concepts specifically highlighted by the RGUKT-Basar TPO and RSG Research evaluators.

---

### Q1: What is Agentic AI and how does it differ from traditional Generative AI?
* **Generative AI**: Focuses on generating text, code, or images based on a static prompt in a single pass (input $\rightarrow$ output). It lacks agency, reflection, and iterative problem-solving.
* **Agentic AI**: Focuses on **autonomous decision-making, reasoning, tool execution, and goal attainment**. An Agentic system uses an LLM as its "reasoning engine" to:
  1. **Perceive** an environment or user goal.
  2. **Plan** multi-step tasks (ReAct pattern: Reason $\rightarrow$ Act $\rightarrow$ Observe).
  3. **Execute Tools** (run SQL queries, call APIs, run Python code).
  4. **Self-Correct / Reflect** (inspect error messages and adjust actions until the goal is achieved).

---

### Q2: What is "Vectorless RAG" and why is it preferred over traditional RAG for Business Intelligence?
* **Traditional Vector RAG**:
  - Chunks text $\rightarrow$ generates vector embeddings $\rightarrow$ stores in a Vector DB (Chroma, FAISS, Pinecone) $\rightarrow$ retrieves chunks via cosine similarity $\rightarrow$ prompts LLM.
  - **Why it FAILS for BI**: Vector similarity cannot perform mathematical aggregations (`SUM`, `AVG`, `GROUP BY`, `ORDER BY`). An LLM given 100 rows in context will hallucinate numbers, make arithmetic errors, and cannot handle thousands of records due to context window limits.
* **Vectorless RAG (Text-to-SQL / Structured RAG)**:
  - Takes natural language questions $\rightarrow$ passes database schema and rules to the agent $\rightarrow$ generates deterministic SQL $\rightarrow$ executes directly in a relational database engine (SQLite, PostgreSQL, Snowflake) $\rightarrow$ formats verified results.
  - **Advantages**: 100% mathematical accuracy, zero arithmetic hallucinations, millisecond execution, handles millions of rows, and provides full SQL auditability.

---

### Q3: What are the prominent Agentic AI Frameworks (LangChain, Google ADK, Dify)?

1. **LangChain & LangGraph**:
   - Open-source Python/TS framework for building context-aware reasoning applications.
   - **LangGraph** models agentic workflows as state machines / cyclical graphs (nodes = actions/tools, edges = conditional transitions). Ideal for human-in-the-loop workflows, multi-agent collaboration, and robust state persistence.
2. **Google ADK (Agent Development Kit)**:
   - Google's toolkit for building modular, multi-turn AI agents integrated with Gemini models, Google Cloud Vertex AI, and enterprise toolchains. Enables grounded reasoning with Google Search and enterprise datastores.
3. **Dify**:
   - An open-source, production-ready LLM application development platform featuring visual workflow builders, RAG pipelines, agentic orchestration, and model management with ready-to-deploy APIs.

---

### Q4: How do you prevent SQL injection and hallucinations in Text-to-SQL assistants?
1. **Multi-layer AST / Regex Guardrails**: Ensure queries start strictly with `SELECT` or `WITH`. Strip out any state-altering commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `ATTACH`).
2. **Statement Splitting Checks**: Disallow multi-statement execution via semicolons (preventing stacked injections like `SELECT * FROM sales; DROP TABLE sales;`).
3. **Table & Column Whitelisting**: Ensure queries only reference permitted tables (`sales_transactions`) and disallow access to system catalogs (`sqlite_master`).
4. **Database-level Permissions**: Connect using read-only database connections or read-only replica users with minimal privilege.
5. **Grounded In-Context Schema**: Provide exact column names, data types, sample values, and clear domain rules in the system prompt so the model never invents columns.
