"""Dump Truck Finance & Leasing Simulator - Streamlit Application Entrypoint."""
import streamlit as st
import simulator

st.set_page_config(
    page_title="Dump Truck Finance & Leasing Simulator",
    page_icon="🚚",
    layout="wide",
)

st.title("🚚 Dump Truck Finance & Leasing Simulator")
st.markdown("### Decision Engine & Portfolio Allocation Tool (V1)")

st.info(
    "Simulator environment initialized. Following `docs/PROGRAMMING_PLAN.md` implementation sequence. "
    "Current status: Step 1 (Project skeleton) complete."
)

# Sidebar placeholder
st.sidebar.header("Global Assumptions")
st.sidebar.text(f"Simulator core v{simulator.__version__}")

# Main tabs placeholder
tab_assumptions, tab_leasing, tab_exploit, tab_results = st.tabs(
    ["Assumptions", "Leasing / Installment", "Exploitation", "Simulation Results"]
)

with tab_assumptions:
    st.subheader("Financing & Procurement Setup")
    st.write("Configurable bank financing terms, batch procurement, and cost matrices will be configured here.")

with tab_leasing:
    st.subheader("Strategy B: Leasing & Installment Plans")
    st.write("Dynamic pricing, deposit options (min 10M FCFA), and 6/12/18/24-month schedules.")

with tab_exploit:
    st.subheader("Strategy C: Direct Fleet Exploitation")
    st.write("Operational profit models (2M - 3M FCFA/month), downtime allowance, and recurring costs.")

with tab_results:
    st.subheader("Comparative Results & Strategy Recommendation")
    st.write("Deterministic monthly simulation comparison across Cash Sale, Leasing, and Exploitation.")

