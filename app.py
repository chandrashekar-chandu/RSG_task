"""
Streamlit Business Intelligence Dashboard
==========================================
Interactive Web UI for the Mini AI Business Intelligence Assistant.
Provides conversational querying, automated visualizations, and SQL transparency.
"""

import streamlit as st
import pandas as pd
import altair as alt
from agent import SalesBIAssistant
from database import get_kpis, get_connection, get_schema_info

# Page configuration
st.set_page_config(
    page_title="Mini AI Business Intelligence Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #3B82F6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
    }
    .answer-card {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-left: 5px solid #22C55E;
        padding: 18px;
        border-radius: 8px;
        margin-bottom: 1.2rem;
        font-size: 1.1rem;
        color: #14532D;
    }
    .unsupported-card {
        background-color: #FFFBEB;
        border: 1px solid #FDE68A;
        border-left: 5px solid #F59E0B;
        padding: 16px;
        border-radius: 8px;
        color: #92400E;
    }
    .security-card {
        background-color: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 5px solid #EF4444;
        padding: 16px;
        border-radius: 8px;
        color: #991B1B;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Assistant
@st.cache_resource
def load_assistant():
    return SalesBIAssistant()

assistant = load_assistant()

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.title("Sales BI Assistant")
    st.markdown("**Architecture**: Vectorless RAG (Text-to-SQL)")
    st.markdown("**Database**: Embedded SQLite")
    st.divider()

    # Executive Overview in Sidebar
    try:
        kpis = get_kpis()
        st.subheader("Dataset Snapshot")
        st.markdown(f"• **Total Transactions**: {kpis['total_records']}")
        st.markdown(f"• **Completed Orders**: {kpis['completed_orders']}")
        st.markdown(f"• **Returned Orders**: {kpis['total_records'] - kpis['completed_orders']}")
        st.markdown(f"• **Total Net Revenue**: ₹{kpis['total_net_revenue']:,.2f}")
        st.markdown(f"• **Top Product**: {kpis['top_product']}")
        st.markdown(f"• **Top Region**: {kpis['top_region']}")
    except Exception as e:
        st.error(f"Error loading KPIs: {e}")

    st.divider()
    st.markdown("### Interview Readiness")
    st.info(
        "**Vectorless RAG**: Queries structured relational data deterministically using validated SQL, "
        "eliminating arithmetic hallucinations common in vector similarity lookups."
    )

# Main Application Layout
st.markdown('<div class="main-title">Mini AI Business Intelligence Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Ask natural language business questions and receive SQL-backed answers with deterministic figures.</div>', unsafe_allow_html=True)

# Tabs
tab_assistant, tab_explorer, tab_architecture = st.tabs(["💬 BI Assistant", "🗄️ Database Explorer", "📐 Architecture & Docs"])

with tab_assistant:
    # KPI Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Net Revenue</div>
            <div class="kpi-value">₹{kpis['total_net_revenue']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Completed Orders</div>
            <div class="kpi-value">{kpis['completed_orders']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Top Product</div>
            <div class="kpi-value">{kpis['top_product']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Peak Sales Month</div>
            <div class="kpi-value">{kpis['peak_month']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Preset Question Quick-Actions
    st.markdown("##### ⚡ Quick Assessment Questions (Click to run):")
    pcol1, pcol2, pcol3, pcol4, pcol5 = st.columns(5)
    
    selected_preset = None
    if pcol1.button("1. Total Revenue", use_container_width=True):
        selected_preset = "What is the total revenue?"
    if pcol2.button("2. Top Product", use_container_width=True):
        selected_preset = "Which product generated the highest revenue?"
    if pcol3.button("3. Monthly Trend", use_container_width=True):
        selected_preset = "What is the monthly revenue trend?"
    if pcol4.button("4. Top Region", use_container_width=True):
        selected_preset = "Which region generated the highest sales?"
    if pcol5.button("5. MoM Changes", use_container_width=True):
        selected_preset = "How did revenue change between two months?"

    # Query Input Box
    default_text = selected_preset if selected_preset else ""
    user_query = st.text_input(
        "Enter your question:",
        value=default_text,
        placeholder="e.g. What is the total revenue? or Which product generated the highest revenue?",
        key="query_input"
    )

    if user_query:
        with st.spinner("Analyzing question, generating SQL & querying database..."):
            result = assistant.process_query(user_query)

        st.markdown("<br>", unsafe_allow_html=True)

        # Status & Response Card
        if result["status"] == "success":
            st.markdown(f'<div class="answer-card">💡 {result["answer"]}</div>', unsafe_allow_html=True)
            
            # Supporting Metrics & Timing
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            with meta_col1:
                st.caption(f"⏱️ **Execution Latency**: {result['latency_ms']} ms")
            with meta_col2:
                st.caption(f"📊 **Result Rows**: {result['row_count']}")
            with meta_col3:
                st.caption("🛡️ **Security Guardrail**: Passed (Read-only SELECT)")

            # SQL Transparency Accordion
            with st.expander("🔍 View Executed SQL Query", expanded=True):
                st.code(result["sql_query"], language="sql")

            # Supporting Data Table & Visualizations
            if result["data"]:
                df_res = pd.DataFrame(result["data"])
                
                col_chart, col_table = st.columns([1, 1])

                with col_chart:
                    st.markdown("##### 📈 Visual Breakdown")
                    # Smart auto-charting based on result schema
                    cols = df_res.columns.tolist()
                    if "month" in cols and ("net_revenue" in cols or "monthly_revenue" in cols):
                        rev_col = "net_revenue" if "net_revenue" in cols else "monthly_revenue"
                        chart = alt.Chart(df_res).mark_line(point=True, color="#2563EB").encode(
                            x=alt.X("month:N", title="Month"),
                            y=alt.Y(f"{rev_col}:Q", title="Revenue (₹)"),
                            tooltip=["month", rev_col]
                        ).properties(height=280)
                        st.altair_chart(chart, use_container_width=True)

                    elif "product" in cols and ("total_net_revenue" in cols or "revenue" in cols):
                        rev_col = "total_net_revenue" if "total_net_revenue" in cols else "revenue"
                        chart = alt.Chart(df_res).mark_bar(color="#3B82F6").encode(
                            x=alt.X(f"{rev_col}:Q", title="Revenue (₹)"),
                            y=alt.Y("product:N", sort="-x", title="Product"),
                            tooltip=["product", rev_col]
                        ).properties(height=280)
                        st.altair_chart(chart, use_container_width=True)

                    elif "region" in cols and ("total_net_revenue" in cols or "total_revenue" in cols):
                        rev_col = "total_net_revenue" if "total_net_revenue" in cols else "total_revenue"
                        chart = alt.Chart(df_res).mark_bar(color="#10B981").encode(
                            x=alt.X("region:N", title="Region"),
                            y=alt.Y(f"{rev_col}:Q", title="Revenue (₹)"),
                            tooltip=["region", rev_col]
                        ).properties(height=280)
                        st.altair_chart(chart, use_container_width=True)

                    elif "absolute_change" in cols:
                        chart = alt.Chart(df_res.dropna(subset=["absolute_change"])).mark_bar().encode(
                            x=alt.X("month:N", title="Month"),
                            y=alt.Y("absolute_change:Q", title="MoM Change (₹)"),
                            color=alt.condition(
                                alt.datum.absolute_change > 0,
                                alt.value("#22C55E"),  # Green for growth
                                alt.value("#EF4444")   # Red for drop
                            ),
                            tooltip=["month", "absolute_change", "percentage_change"]
                        ).properties(height=280)
                        st.altair_chart(chart, use_container_width=True)
                    else:
                        st.info("Chart view not applicable for single summary figure.")

                with col_table:
                    st.markdown("##### 📋 Supporting Figures (Raw Result)")
                    st.dataframe(df_res, use_container_width=True)

        elif result["status"] == "security_violation":
            st.markdown(f'<div class="security-card">🚨 <b>Security Guardrail Alert:</b><br>{result["answer"]}</div>', unsafe_allow_html=True)
            if result["sql_query"]:
                st.code(result["sql_query"], language="sql")

        else:
            st.markdown(f'<div class="unsupported-card">⚠️ {result["answer"]}</div>', unsafe_allow_html=True)

with tab_explorer:
    st.subheader("Cleaned SQLite Transactions Dataset")
    st.caption("Cleaned records stored in `sales_bi.db` with missing prices imputed and ISO dates.")
    
    conn = get_connection()
    df_all = pd.read_sql_query("SELECT * FROM sales_transactions ORDER BY order_date ASC;", conn)
    conn.close()

    # Filter Controls
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        sel_region = st.multiselect("Filter Region:", options=df_all["region"].unique(), default=df_all["region"].unique())
    with fcol2:
        sel_product = st.multiselect("Filter Product:", options=df_all["product"].unique(), default=df_all["product"].unique())
    with fcol3:
        sel_status = st.multiselect("Filter Status:", options=df_all["status"].unique(), default=df_all["status"].unique())

    filtered_df = df_all[
        (df_all["region"].isin(sel_region)) &
        (df_all["product"].isin(sel_product)) &
        (df_all["status"].isin(sel_status))
    ]

    st.dataframe(filtered_df, use_container_width=True, height=400)
    st.caption(f"Showing {len(filtered_df)} of {len(df_all)} records.")

with tab_architecture:
    st.subheader("Architecture & Vectorless RAG Workflow")
    st.markdown("""
    ### Why Vectorless RAG?
    Traditional RAG relies on semantic embeddings and similarity search across text chunks. It fails for business intelligence because:
    1. **Vector similarity cannot compute aggregations**: It cannot reliably sum numbers, calculate averages, or determine group-by rankings.
    2. **Arithmetic Hallucinations**: Standard LLMs hallucinate calculations when dealing with hundreds of rows.
    
    **Vectorless RAG (Text-to-SQL)** solves this by:
    - Converting natural language questions into deterministic SQL queries against structured databases.
    - Passing generated queries through strict **Security Guardrails** (validating read-only operations, preventing SQL injections).
    - Executing against relational databases (SQLite) to obtain 100% accurate, verifiable mathematical figures.
    - Synthesizing business narratives backed directly by executed data.
    """)
    st.image("https://mermaid.ink/svg/pako:eNpFUMtqw0AM_BXhUwn0B-QcCs0llEDwIYXUuNjK1m6tld2l5bUh5N_rOKGkpSfaGXk0u0CjTaAD1617OQWfTjX51Fz2fS5e2hV_e-zW58vl5V1d4yX43I0eNqY2dG-4uTq2718e4R9g4Vj2z2GgC6FpG9uG9g6O5m3w8y24v0e194Z31pkyYw_O9o46p0fK1t_Kj0-U", caption="Vectorless RAG Flow")
