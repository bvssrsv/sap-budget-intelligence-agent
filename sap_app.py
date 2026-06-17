import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph_sap_agent import sap_agent

st.set_page_config(page_title="SAP Budget Intelligence", layout="wide")
st.title("SAP Budget Intelligence Agent")
st.caption("Powered by LangGraph + Claude | Ask questions about budget data, hierarchies, and variances")

with st.sidebar:
    st.markdown("### Sample Questions")
    st.markdown("""
- List all cost centers
- Show budget summary for CORP
- What are the top expenses for Manufacturing?
- Monthly trend for cost center 9
- Compare budget across all business units
- Which SALES cost center has the highest revenue?
- Show me OPEX breakdown for IT department
""")
    st.markdown("---")
    st.markdown("### Architecture")
    st.markdown("""
    **UI**: Streamlit  
    **Agent**: LangGraph  
    **LLM**: Claude Sonnet  
    **Data**: Mock SAP OData API  
    """)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if prompt := st.chat_input("Ask about budget data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Querying SAP..."):
            result = sap_agent.invoke({"messages": [HumanMessage(content=prompt)]})
            response = result["messages"][-1].content
            st.write(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})