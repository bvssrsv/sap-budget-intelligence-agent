import httpx
from typing import Annotated, TypedDict
import json

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool

SAP_BASE = "http://localhost:5000"

# ==================== TOOLS ====================

@tool
def get_budget_data(costcenter: str = "", cc_node: str = "", ce_node: str = "") -> str:
    """Fetch monthly budget data from SAP.
    Filter by costcenter (single CC like '1'), 
    cc_node (group like 'CORP', 'MFG', 'MARKET', 'SALES'),
    or ce_node (type like 'OPEX', 'COGS', 'REVENUE')."""
    try:
        params = {}
        if costcenter:
            params["costcenter"] = costcenter
        if cc_node:
            params["cc_node"] = cc_node
        if ce_node:
            params["ce_node"] = ce_node
        
        response = httpx.get(f"{SAP_BASE}/sap/odata/BUDGET_DATA", params=params, timeout=10)
        records = response.json().get("d", {}).get("results", [])
        if not records:
            return f"No data found for the given filters."
        return json.dumps(records, indent=2)
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def list_cost_centers(node: str = "") -> str:
    """List cost centers. Optionally filter by node (CORP, MFG, MARKET, SALES)."""
    try:
        params = {"node": node} if node else {}
        response = httpx.get(f"{SAP_BASE}/sap/odata/COSTCENTER", params=params, timeout=5)
        centers = response.json().get("d", {}).get("results", [])
        lines = []
        for c in centers:
            lines.append(f"CC {c['ID']}: {c['DESCRIPTION']} (Node: {c['NODE']}/{c['NODE1']}, Co: {c['COMPANY_CODE']})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def list_cost_elements(node: str = "") -> str:
    """List cost elements. Optionally filter by node (OPEX, COGS, REVENUE)."""
    try:
        params = {"node": node} if node else {}
        response = httpx.get(f"{SAP_BASE}/sap/odata/COSTELMNT", params=params, timeout=5)
        elements = response.json().get("d", {}).get("results", [])
        lines = []
        for e in elements:
            lines.append(f"CE {e['ID']}: {e['DESCRIPTION']} (Node: {e['NODE']}/{e['NODE1']})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def analyze_budget(costcenter: str = "", cc_node: str = "", analysis_type: str = "summary") -> str:
    """Analyze budget data with domain intelligence.
    analysis_type options:
    - 'summary': total by cost element category
    - 'monthly_trend': month over month changes
    - 'top_expenses': largest cost elements
    - 'node_comparison': compare across CC nodes"""
    try:
        params = {}
        if costcenter:
            params["costcenter"] = costcenter
        if cc_node:
            params["cc_node"] = cc_node
            
        response = httpx.get(f"{SAP_BASE}/sap/odata/BUDGET_DATA", params=params, timeout=10)
        records = response.json().get("d", {}).get("results", [])
        
        if not records:
            return "No data found."
        
        if analysis_type == "summary":
            # Summarize by cost element node
            by_node = {}
            for r in records:
                node = r["COSTELMNT_NODE1"]
                by_node[node] = by_node.get(node, 0) + r["AMOUNT"]
            
            total = sum(by_node.values())
            lines = [f"Budget Summary (Total: ${total:,.0f})"]
            for node, amt in sorted(by_node.items(), key=lambda x: -x[1]):
                pct = (amt / total * 100) if total else 0
                lines.append(f"  {node}: ${amt:,.0f} ({pct:.1f}%)")
            return "\n".join(lines)
        
        elif analysis_type == "monthly_trend":
            # Monthly totals
            by_month = {}
            for r in records:
                m = r["TIME"]
                by_month[m] = by_month.get(m, 0) + r["AMOUNT"]
            
            months_order = ["2026.JAN","2026.FEB","2026.MAR","2026.APR","2026.MAY","2026.JUN",
                          "2026.JUL","2026.AUG","2026.SEP","2026.OCT","2026.NOV","2026.DEC"]
            
            lines = ["Monthly Trend:"]
            prev = None
            for m in months_order:
                val = by_month.get(m, 0)
                if prev is not None and prev != 0:
                    chg = ((val - prev) / prev) * 100
                    arrow = "+" if chg > 0 else ""
                    lines.append(f"  {m}: ${val:,.0f} ({arrow}{chg:.1f}%)")
                else:
                    lines.append(f"  {m}: ${val:,.0f}")
                prev = val
            return "\n".join(lines)
        
        elif analysis_type == "top_expenses":
            # Top cost elements by total amount
            by_ce = {}
            for r in records:
                key = f"{r['COSTELMNT']} ({r['COSTELMNT_NODE1']})"
                by_ce[key] = by_ce.get(key, 0) + r["AMOUNT"]
            
            sorted_ce = sorted(by_ce.items(), key=lambda x: -x[1])[:10]
            lines = ["Top 10 Cost Elements:"]
            for i, (ce, amt) in enumerate(sorted_ce, 1):
                lines.append(f"  {i}. {ce}: ${amt:,.0f}")
            return "\n".join(lines)
        
        elif analysis_type == "node_comparison":
            # Compare across CC nodes
            by_cc_node = {}
            for r in records:
                node = r["COSTCENTER_NODE"]
                by_cc_node[node] = by_cc_node.get(node, 0) + r["AMOUNT"]
            
            lines = ["Comparison by Business Unit:"]
            for node, amt in sorted(by_cc_node.items(), key=lambda x: -x[1]):
                lines.append(f"  {node}: ${amt:,.0f}")
            return "\n".join(lines)
        
        return "Unknown analysis type."
    except Exception as e:
        return f"Error: {str(e)}"

tools = [get_budget_data, list_cost_centers, list_cost_elements, analyze_budget]

# ==================== LANGGRAPH AGENT ====================

SYSTEM_PROMPT = """You are an SAP Budget Intelligence Agent. You help finance teams analyze 
budget data from SAP BPC. You understand cost center hierarchies (CORP, MFG, MARKET, SALES), 
cost element categories (OPEX, COGS, REVENUE), and financial planning concepts.

When answering questions:
- Use the available tools to fetch real data before answering
- Provide specific numbers, not vague summaries
- Flag unusual patterns (large variances, seasonal spikes, concentration risk)
- Present data clearly with totals and percentages where relevant

Available hierarchy nodes:
- Cost Center Nodes: CORP (Finance/Legal/IT/HR), MFG (Manufacturing), MARKET (Marketing), SALES
- Cost Element Nodes: OPEX (SG&A, R&D, D&A), COGS (Materials, Labor, Overhead), REVENUE (Sales)
"""

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
llm_with_tools = llm.bind_tools(tools)

def agent(state: AgentState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    return {"messages": [llm_with_tools.invoke(messages)]}

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
workflow.add_node("tools", ToolNode(tools))

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

sap_agent = workflow.compile()

# ==================== INTERACTIVE DEMO ====================
if __name__ == "__main__":
    print("SAP Budget Intelligence Agent Ready!\n")
    print("Try these:")
    print("  - List all cost centers")
    print("  - What are the top expenses for CORP?")
    print("  - Show monthly trend for cost center 5")
    print("  - Compare OPEX vs COGS across business units")
    print("  - Which cost center has the highest budget?\n")
    
    while True:
        q = input("You: ")
        if q.lower() in ["exit", "quit"]:
            break
        result = sap_agent.invoke({"messages": [HumanMessage(content=q)]})
        print("Agent:", result["messages"][-1].content)