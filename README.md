# SAP Budget Intelligence Agent

An AI-powered agent that queries SAP budget data using natural language. Built with LangGraph, Claude Sonnet, and Streamlit.

## What It Does

Ask plain English questions about budget data and get instant answers:
- "What is the budget for cost center 5?"
- "Show me the top expenses for Manufacturing"
- "Compare OPEX vs COGS across business units"
- "Which cost center has the highest budget?"

## Architecture

User → Streamlit Chat UI → LangGraph Agent → Claude Sonnet (LLM) → Mock SAP OData API (Flask)
The agent decides which tools to call based on the question — it's not a fixed workflow. Claude interprets the question, picks the right tool, and formats the response.

## Components

- **sap_app.py** — Streamlit chat interface
- **langgraph_sap_agent.py** — LangGraph agent with tools (get_budget_data, list_cost_centers, list_cost_elements, analyze_budget), connected to Claude via Anthropic API
- **mock_sap_server.py** — Flask server that reads from Sample_Budget.xlsx and serves data as OData-style JSON, simulating SAP Gateway
- **Sample_Budget.xlsx** — Budget data with Cost Center hierarchy, Cost Element hierarchy, and monthly budget amounts

## How to Run

Open two terminals:

Terminal 1 — start the mock SAP server:

Terminal 2 — start the Streamlit UI:

## Requirements
You'll need an Anthropic API key set as an environment variable.

## Why This Matters

In a real SAP environment, swap the Flask mock server URL with an SAP Gateway OData endpoint — the agent, tools, and prompts stay identical. The architecture is production-ready; only the data source changes.

Budget analysts spend 40+ hours per cycle on pre-BPC and post-BPC Excel work. This agent automates the question-and-answer layer — anomaly detection, variance analysis, hierarchy drill-downs — using domain-aware AI instead of manual spreadsheet work.

## Built With

- LangGraph (agent orchestration)
- Claude Sonnet (Anthropic API)
- Flask (mock SAP OData server)
- Streamlit (chat UI)
- Python

- 

