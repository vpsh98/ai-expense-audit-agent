# AI Expense Audit Agent

An enterprise-ready, portfolio/KRA-grade **AI Expense Audit Agent** designed to demonstrate genuine agentic workflows, multi-tool orchestration, LLM reasoning, policy compliance validation, arithmetic tool execution, and evidence-backed audit reporting.

---

## 🎯 Overview

Expense auditing in organizations often involves tedious manual cross-referencing between submitted line items, corporate policies, manager approval records, and receipt images. 

This project demonstrates a production-structured **autonomous AI agent** that:
1. Receives an audit request for an employee's expense claim.
2. Dynamically decides which data sources and tools to query.
3. Sequentially executes tools to retrieve employee metadata, expense records, policy thresholds, and pre-approved exceptions.
4. Uses a dedicated calculation tool for exact financial math (avoiding LLM arithmetic hallucination).
5. Cross-checks receipts against expense line items for verification.
6. Classifies every expense with clear evidence-backed audit findings.
7. Renders real-time human-readable tool activity in a Streamlit UI and generates downloadable executive audit reports (Markdown, JSON, HTML).

---

## 🏗️ Architecture & Component Interaction

The system is built with strict separation of concerns, ensuring transparent state management and clear tool execution loops:

```
                  +-----------------------+
                  |     Streamlit UI      |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  |  Expense Audit Agent  | (LLM Loop & Orchestration)
                  +-----------+-----------+
                              |
         +--------------------+--------------------+
         |                    |                    |
         v                    v                    v
+------------------+ +------------------+ +------------------+
|  Tool Registry   | | Data Repositories| |  Domain Models   |
+------------------+ +------------------+ +------------------+
| get_employee     | | employees.json   | | AuditSummary     |
| read_expenses    | | expenses.csv     | | AuditFinding     |
| search_policy    | | approvals.json   | | AgentStep        |
| check_approval   | | receipts/        | | ToolResult       |
| calculate        | +------------------+ +------------------+
| read_receipt     |
+------------------+
```

---

## 🛠️ Key Technical Features & Patterns

* **Explicit ReAct / Tool Loop:** Unrolls LLM tool calls step-by-step to expose function selection, parameter parsing, execution, and output handling without opaque black-box frameworks.
* **Deterministic Arithmetic Tooling (`calculate`):** Offloads mathematical operations (excess calculation, variances, percentage differences) to code to maintain 100% financial precision.
* **Evidence-Backed Findings:** Every audit finding attaches direct citations (policy limits, approval IDs, receipt values) to guarantee explainability and trust.
* **5 Core Audit Classifications:**
  - `COMPLIANT`: Within policy limits with valid details.
  - `POLICY_EXCEPTION`: Exceeds policy cap BUT pre-approved via manager approval.
  - `MISSING_APPROVAL`: Exceeds policy cap WITHOUT prior manager approval.
  - `RECEIPT_MISMATCH`: Claimed amount or date differs from physical receipt total.
  - `MISSING_DOCUMENT`: Mandatory receipt required by policy is missing.
  - `REQUIRES_REVIEW`: Date anomalies or duplicate claim submissions.
* **Multi-Format Executive Reporting:** Export audit summaries to GitHub-Flavored Markdown, JSON compliance payloads, and presentation-ready HTML reports.
* **Offline Mock Transport & Live LLM Client:** Operates seamlessly offline with deterministic mock mode for testing/demos or live with Google Gemini (`google-genai` SDK) / OpenAI API keys.

---

## ⚡ Quick Start & Setup Guide

### 1. Installation & Environment Setup

```bash
# Clone or navigate to the project directory
cd ai-expense-audit-agent

# Create virtual environment (optional)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and set your optional API keys or flags:

```bash
GEMINI_API_KEY=your_google_gemini_api_key_here
LLM_MODEL=gemini-3.8-flash
MOCK_LLM_MODE=False
LOG_LEVEL=INFO
```

> *Note: If no API key is set or `MOCK_LLM_MODE=True`, the agent operates seamlessly in offline mock mode.*

---

## 🚀 Running the Streamlit UI

Launch the interactive web dashboard:

```bash
streamlit run src/ui/app.py
```

Open `http://localhost:8501` in your web browser to:
- Select sample employees (Rajesh Kumar, Vikram Patel, Ananya Sharma, Priya Nair).
- Upload custom `.csv` or `.xlsx` expense files.
- Watch real-time agent execution status cards in the **Activity Feed**.
- View KPI summary cards, color-coded findings table, and download audit reports (`.md`, `.json`, `.html`).

---

## 🧪 Running Unit & Integration Tests

Run the full automated pytest suite (55+ tests):

```bash
pytest
```

Run specific test modules:

```bash
# Run end-to-end integration scenario tests
pytest tests/test_e2e_scenarios.py

# Run UI component tests
pytest tests/test_ui_components.py tests/test_ui_results.py

# Run domain tool & repository tests
pytest tests/test_domain_tools.py tests/test_repositories.py
```

---

## 📂 Directory Structure

```
ai-expense-audit-agent/
│
├── README.md               # Master project overview & setup guide
├── ARCHITECTURE.md         # System architecture & sequence diagrams
├── data/                   # Mock enterprise datasets (CSV, JSON, receipts)
│   ├── employees.json
│   ├── expenses.csv
│   ├── approvals.json
│   ├── policies.json
│   ├── demo_scenarios.json
│   └── receipts/
├── src/                    # Core source code
│   ├── agent/              # Agent orchestration, prompts & LLM client
│   ├── tools/              # Tool definitions (calculate, employee, policy, approval, receipt)
│   ├── data/               # Data access repositories
│   ├── models/             # Pydantic v2 domain schemas & enums
│   ├── reporting/          # Audit summary & report generators (MD, JSON, HTML)
│   └── ui/                 # Streamlit web application & components
└── tests/                  # Automated unit and E2E integration test suite
```
