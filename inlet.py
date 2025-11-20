import streamlit as st
import pandas as pd

# Page Configuration - centered layout is often better for mobile focus
st.set_page_config(
    page_title="ParaInlet",
    page_icon="✈️",
    layout="centered" 
)

# Title
st.title("ParaInlet")
st.caption("Aerodynamic Inlet Parameter Calculator")

# Initialize Session State
if 'inlets' not in st.session_state:
    st.session_state.inlets = []

# --- Configuration ---
with st.container():
    st.write("### Setup")
    # Number of Inlets
    num_inlets = st.number_input(
        "Number of Inlets", 
        min_value=1, 
        max_value=10, 
        value=1
    )

# State Management: Resize inlet list
current_count = len(st.session_state.inlets)
if current_count < num_inlets:
    for i in range(current_count, num_inlets):
        st.session_state.inlets.append({
            "name": f"Inlet {i+1}",
            "gamma": 1.4, 
            "mach": 2.0, 
            "pr_th": 0.98,
            "pt_i": 101325.0, 
            "pt_e": 95000.0, 
            "tt_i": 300.0, 
            "tt_e": 350.0, 
            "t_i": 280.0, 
            "t_e": 330.0
        })
elif current_count > num_inlets:
    st.session_state.inlets = st.session_state.inlets[:num_inlets]

st.divider()

# --- Inputs (Tabs for Mobile Friendliness) ---
if num_inlets > 0:
    st.write("### Parameters")
    tabs = st.tabs([f"Inlet {i+1}" for i in range(num_inlets)])
    for i, tab in enumerate(tabs):
        with tab:
            d = st.session_state.inlets[i]
            
            # Name
            d["name"] = st.text_input("Name", d["name"], key=f"n{i}")
            
            # Flow
            st.caption("Flow Properties")
            c1, c2 = st.columns(2)
            d["gamma"] = c1.number_input("Gamma (γ)", value=d["gamma"], key=f"g{i}", format="%.2f")
            d["mach"] = c2.number_input("Mach (Mi)", value=d["mach"], key=f"m{i}", format="%.2f")
            d["pr_th"] = st.number_input("Theor. PR (Pt,e/Pt,i)th", value=d["pr_th"], key=f"pr{i}", format="%.3f")
            
            # Pressure
            st.caption("Total Pressures (Pa)")
            d["pt_i"] = st.number_input("Inlet (Pt,i)", value=d["pt_i"], key=f"pti{i}")
            d["pt_e"] = st.number_input("Exit (Pt,e)", value=d["pt_e"], key=f"pte{i}")
            
            # Temperature
            st.caption("Temperatures (K)")
            tc1, tc2 = st.columns(2)
            d["tt_i"] = tc1.number_input("Total T In (Tt,i)", value=d["tt_i"], key=f"tti{i}")
            d["tt_e"] = tc2.number_input("Total T Out (Tt,e)", value=d["tt_e"], key=f"tte{i}")
            d["t_i"] = tc1.number_input("Static T In (Ti)", value=d["t_i"], key=f"ti{i}")
            d["t_e"] = tc2.number_input("Static T Out (Te)", value=d["t_e"], key=f"te{i}")

st.divider()

# --- Calculation Logic ---
def calculate_parameters(data):
    # 1. Total Pressure Recovery (π)
    recovery = data["pt_e"] / data["pt_i"] if data["pt_i"] != 0 else 0
    
    # 2. Kinetic Energy Efficiency (ηKE)
    ke_eff = 0.0
    if data["mach"] > 0 and data["gamma"] > 1 and data["pt_e"] > 0:
        term1 = 1 / (data["gamma"] - 1)
        term2 = 1 / (data["mach"]**2)
        base = data["pt_i"] / data["pt_e"]
        if base > 0:
            exponent = (data["gamma"] - 1) / data["gamma"]
            temp_ratio = data["tt_e"] / data["tt_i"] if data["tt_i"] != 0 else 1
            bracket = (temp_ratio * (base**exponent)) - 1
            ke_eff = 1 - (term1 * term2 * bracket)
            
    # 3. Adiabatic Compression Efficiency (ηcomp)
    ad_eff = 0.0
    static_temp_ratio = data["t_e"] / data["t_i"] if data["t_i"] != 0 else 1
    if (static_temp_ratio - 1) != 0:
        num = (data["gamma"] - 1) * (data["mach"]**2) / 2
        term2 = (1 - ke_eff) / (static_temp_ratio - 1)
        ad_eff = 1 - (num * term2)
        
    # 4. Shock Compression Efficiency (ηshock)
    shock_eff = 0.0
    if data["pr_th"] > 0:
        shock_eff = recovery / data["pr_th"]
        
    return {
        "Name": data["name"],
        "Recovery": recovery,
        "KE Eff (%)": ke_eff * 100,
        "Adiabatic Eff (%)": ad_eff * 100,
        "Shock Eff (%)": shock_eff * 100
    }

# --- Main Content Area ---
if st.button("Calculate Results", type="primary", use_container_width=True):
    
    # Perform Calculations
    results = [calculate_parameters(inlet) for inlet in st.session_state.inlets]
    df = pd.DataFrame(results)
    
    # 1. Data Table
    st.subheader("📊 Summary")
    st.dataframe(
        df.style.format({
            "Recovery": "{:.4f}",
            "KE Eff (%)": "{:.2f}%",
            "Adiabatic Eff (%)": "{:.2f}%",
            "Shock Eff (%)": "{:.2f}%"
        }),
        use_container_width=True
    )
    
    # 2. Visualizations
    st.subheader("📈 Charts")
    chart_df = df.set_index("Name")
    
    st.markdown("##### Kinetic Energy Efficiency (%)")
    st.bar_chart(chart_df["KE Eff (%)"], use_container_width=True)
    
    st.markdown("##### Adiabatic Comp. Efficiency (%)")
    st.bar_chart(chart_df["Adiabatic Eff (%)"], use_container_width=True)
    
    st.markdown("##### Pressure Recovery (π)")
    st.bar_chart(chart_df["Recovery"], use_container_width=True)

else:
    st.info("Enter parameters and click Calculate.")