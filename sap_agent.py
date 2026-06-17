import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

# Tool 1: Get budget data from mock SAP
@tool
def get_budget_data(costcenter: str) -> str:
    """Get monthly budget data for a cost center from SAP"""
    response = httpx.get(f"http://localhost:5000/sap/odata/BUDGET_DATA?costcenter={costcenter}&scenario=ESTIMATE")
    data = response.json()
    records = data["d"]["results"]
    if not records:
        return f"No data found for cost center {costcenter}"
    
    lines = []
    for r in records:
        lines.append(f"{r['COSTELMNT']} | {r['TIME']} | ${r['AMOUNT']:,}")
    return "\n".join(lines)

# Set up Claude with the tool
llm = ChatAnthropic(model="claude-sonnet-4-6")
llm_with_tools = llm.bind_tools([get_budget_data])

# Ask a question
response = llm_with_tools.invoke("What is the budget for cost center 200?")
print(response)