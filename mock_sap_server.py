from flask import Flask, jsonify, request
import pandas as pd

app = Flask(__name__)

# ==================== LOAD DATA FROM EXCEL ====================
EXCEL_FILE = r"C:\Users\dell\Downloads\Sample Budget.xlsx"

# Load cost centers
cc_df = pd.read_excel(EXCEL_FILE, sheet_name="Cost Center")
cc_df.columns = cc_df.columns.str.strip()

# Load cost elements
ce_df = pd.read_excel(EXCEL_FILE, sheet_name="Cost Element")
ce_df.columns = ce_df.columns.str.strip()

# Load budget data and normalize from cross-tab to rows
budget_raw = pd.read_excel(EXCEL_FILE, sheet_name="Budget Data")
budget_raw.columns = budget_raw.columns.str.strip()

# Identify month columns
month_columns = [c for c in budget_raw.columns if "2026" in str(c)]

# Map column names to standard time format (2026.JAN, 2026.FEB, etc.)
month_map = {}
for col in month_columns:
    clean = col.strip().lower()
    if "jan" in clean: month_map[col] = "2026.JAN"
    elif "feb" in clean: month_map[col] = "2026.FEB"
    elif "mar" in clean: month_map[col] = "2026.MAR"
    elif "apr" in clean: month_map[col] = "2026.APR"
    elif "may" in clean: month_map[col] = "2026.MAY"
    elif "jun" in clean: month_map[col] = "2026.JUN"
    elif "jul" in clean: month_map[col] = "2026.JUL"
    elif "aug" in clean: month_map[col] = "2026.AUG"
    elif "sep" in clean: month_map[col] = "2026.SEP"
    elif "oct" in clean: month_map[col] = "2026.OCT"
    elif "nov" in clean: month_map[col] = "2026.NOV"
    elif "dec" in clean: month_map[col] = "2026.DEC"

# Melt budget data into normalized rows
id_cols = ["Scenario", "Cost Center Node", "Cost Center Node.1", 
           "Cost Center", "Cost Element Node", "Cost Element Node.1",
           "Cost Element", "Description"]

budget_df = budget_raw.melt(
    id_vars=id_cols,
    value_vars=month_columns,
    var_name="MONTH_COL",
    value_name="AMOUNT"
)
budget_df["TIME"] = budget_df["MONTH_COL"].map(month_map)
budget_df["AMOUNT"] = pd.to_numeric(budget_df["AMOUNT"], errors="coerce").fillna(0)

# Convert IDs to strings for consistent matching
budget_df["Cost Center"] = budget_df["Cost Center"].astype(str)
budget_df["Cost Element"] = budget_df["Cost Element"].astype(str)
cc_df["Cost Center"] = cc_df["Cost Center"].astype(str)
ce_df["Cost Element"] = ce_df["Cost Element"].astype(str)

print(f"Loaded {len(cc_df)} cost centers, {len(ce_df)} cost elements, {len(budget_df)} budget records")

# ==================== API ENDPOINTS ====================

@app.route('/sap/odata/COSTCENTER', methods=['GET'])
def get_cost_centers():
    node = request.args.get('node', '')
    if node:
        filtered = cc_df[cc_df["Cost Center Node"] == node]
    else:
        filtered = cc_df
    
    results = []
    for _, row in filtered.iterrows():
        results.append({
            "ID": str(row["Cost Center"]),
            "DESCRIPTION": str(row["Cost center name"]),
            "NODE": str(row["Cost Center Node"]),
            "NODE1": str(row["Cost Center Node.1"]),
            "COMPANY_CODE": str(row["Company Code"]),
            "DEPARTMENT": str(row["Department"])
        })
    return jsonify({"d": {"results": results}})

@app.route('/sap/odata/COSTELMNT', methods=['GET'])
def get_cost_elements():
    node = request.args.get('node', '')
    if node:
        filtered = ce_df[ce_df["Cost Element Node"] == node]
    else:
        filtered = ce_df
    
    results = []
    for _, row in filtered.iterrows():
        results.append({
            "ID": str(row["Cost Element"]),
            "DESCRIPTION": str(row.get("Cost Element Description 1", "")),
            "NODE": str(row["Cost Element Node"]),
            "NODE1": str(row["Cost Element Node.1"])
        })
    return jsonify({"d": {"results": results}})

@app.route('/sap/odata/BUDGET_DATA', methods=['GET'])
def get_budget_data():
    cc = request.args.get('costcenter', '')
    scenario = request.args.get('scenario', '')
    ce_node = request.args.get('ce_node', '')
    cc_node = request.args.get('cc_node', '')
    
    filtered = budget_df.copy()
    
    if cc:
        filtered = filtered[filtered["Cost Center"] == cc]
    if scenario:
        filtered = filtered[filtered["Scenario"] == scenario]
    if ce_node:
        filtered = filtered[filtered["Cost Element Node"] == ce_node]
    if cc_node:
        filtered = filtered[filtered["Cost Center Node"] == cc_node]
    
    # Exclude zero amounts
    filtered = filtered[filtered["AMOUNT"] != 0]
    
    results = []
    for _, row in filtered.iterrows():
        results.append({
            "COSTCENTER": str(row["Cost Center"]),
            "COSTCENTER_NODE": str(row["Cost Center Node"]),
            "COSTCENTER_NODE1": str(row["Cost Center Node.1"]),
            "COSTELMNT": str(row["Cost Element"]),
            "COSTELMNT_NODE": str(row["Cost Element Node"]),
            "COSTELMNT_NODE1": str(row["Cost Element Node.1"]),
            "SCENARIO": str(row["Scenario"]),
            "DESCRIPTION": str(row["Description"]),
            "TIME": str(row["TIME"]),
            "AMOUNT": float(row["AMOUNT"])
        })
    
    return jsonify({"d": {"results": results}})

# ==================== TABLE VIEW ====================

@app.route('/view/budget', methods=['GET'])
def view_budget():
    cc = request.args.get('costcenter', '')
    cc_node = request.args.get('cc_node', '')
    
    filtered = budget_df.copy()
    if cc:
        filtered = filtered[filtered["Cost Center"] == cc]
    elif cc_node:
        filtered = filtered[filtered["Cost Center Node"] == cc_node]
    else:
        filtered = filtered.head(100)
    
    months = ["2026.JAN","2026.FEB","2026.MAR","2026.APR","2026.MAY","2026.JUN",
              "2026.JUL","2026.AUG","2026.SEP","2026.OCT","2026.NOV","2026.DEC"]
    
    # Pivot for display
    pivot = filtered.pivot_table(
        index=["Cost Center", "Cost Element", "Cost Element Node.1"],
        columns="TIME",
        values="AMOUNT",
        aggfunc="sum"
    ).fillna(0)
    
    html = "<h3>Budget Data</h3>"
    html += "<table border='1' cellpadding='5' style='border-collapse:collapse; font-size:13px'>"
    html += "<tr><th>CC</th><th>CE</th><th>Category</th>"
    for m in months:
        html += f"<th>{m.split('.')[1]}</th>"
    html += "<th><b>TOTAL</b></th></tr>"
    
    for idx, row in pivot.iterrows():
        cc_val, ce_val, cat = idx
        html += f"<tr><td>{cc_val}</td><td>{ce_val}</td><td>{cat}</td>"
        total = 0
        for m in months:
            val = int(row.get(m, 0))
            total += val
            html += f"<td style='text-align:right'>{val:,}</td>"
        html += f"<td style='text-align:right'><b>{total:,}</b></td></tr>"
    html += "</table>"
    return html

@app.route('/view/hierarchy', methods=['GET'])
def view_hierarchy():
    """View cost center and cost element hierarchy"""
    html = "<h3>Cost Center Hierarchy</h3><table border='1' cellpadding='5'>"
    html += "<tr><th>Node</th><th>Sub-Node</th><th>CC ID</th><th>Name</th><th>Company Code</th></tr>"
    for _, row in cc_df.iterrows():
        html += f"<tr><td>{row['Cost Center Node']}</td><td>{row['Cost Center Node.1']}</td>"
        html += f"<td>{row['Cost Center']}</td><td>{row['Cost center name']}</td>"
        html += f"<td>{row['Company Code']}</td></tr>"
    html += "</table>"
    
    html += "<h3>Cost Element Hierarchy</h3><table border='1' cellpadding='5'>"
    html += "<tr><th>Node</th><th>Sub-Node</th><th>CE ID</th><th>Description</th></tr>"
    for _, row in ce_df.iterrows():
        desc = row.get("Cost Element Description 1", "")
        html += f"<tr><td>{row['Cost Element Node']}</td><td>{row['Cost Element Node.1']}</td>"
        html += f"<td>{row['Cost Element']}</td><td>{desc}</td></tr>"
    html += "</table>"
    return html

if __name__ == '__main__':
    app.run(debug=True, port=5000)