import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from scipy.interpolate import interp1d
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Tensile Suite - Master Curve", layout="wide")

if 'samples' not in st.session_state:
    st.session_state.samples = {}

# --- 2. Professional Header & Logo ---
logo_url = "https://raw.githubusercontent.com/12solo/Tensile-test-extrapolator/main/logo%20s.png"
col_logo, col_text = st.columns([1, 5])
with col_logo:
    try: st.image(logo_url, width=150)
    except: st.header("🔬")
with col_text:
    st.title("Solomon Tensile Suite v2.1")
    st.markdown("**Statistical Master Curve Generator** 🚀")

# --- 3. Sidebar: Global Parameters ---
st.sidebar.header("📂 Global Metadata")
project_name = st.sidebar.text_input("Project Name", "Polymer Variability Study")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Gauge Length (mm)", value=50.0)
target_def = st.sidebar.number_input("Target Extrapolation (mm)", value=400.0)

if st.sidebar.button("Clear All Data"):
    st.session_state.samples = {}
    st.rerun()

# --- 4. Main Interface: Upload & Process ---
st.subheader("1. Add Samples to Dataset")
uploaded_file = st.file_uploader("Upload Sample (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    sample_name = st.text_input("Sample Label", uploaded_file.name.split('.')[0])
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    cols = df_raw.columns.tolist()
    
    c1, c2 = st.columns(2)
    with c1: f_col = st.selectbox(f"Force Column", cols, key=f"f_{sample_name}")
    with c2: d_col = st.selectbox(f"Deformation Column", cols, key=f"d_{sample_name}")
    
    if st.button(f"Add {sample_name}"):
        # Standardize to Stress-Strain
        stress = df_raw[f_col].values / area
        strain = (df_raw[d_col].values / gauge_length) * 100
        
        # Extrapolate to target
        slope, _ = np.polyfit(strain[-30:], stress[-30:], 1)
        target_strain = (target_def / gauge_length) * 100
        strain_ext = np.linspace(strain[-1], target_strain, 100)
        stress_ext = stress[-1] + slope * (strain_ext - strain[-1])
        
        full_strain = np.concatenate([strain, strain_ext[1:]])
        full_stress = np.concatenate([stress, stress_ext[1:]])
        
        st.session_state.samples[sample_name] = {"strain": full_strain, "stress": full_stress}
        st.success(f"Successfully added {sample_name}")

# --- 5. Master Curve Engine ---
if st.session_state.samples:
    st.divider()
    st.subheader("2. Master Curve Analysis")
    
    # Create common strain grid for averaging
    max_target_strain = (target_def / gauge_length) * 100
    common_strain = np.linspace(0, max_target_strain, 500)
    
    all_interp_stress = []
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for name, data in st.session_state.samples.items():
        # Interpolate each sample onto the common grid
        f_interp = interp1d(data['strain'], data['stress'], bounds_error=False, fill_value="extrapolate")
        interp_stress = f_interp(common_strain)
        all_interp_stress.append(interp_stress)
        
        # Plot individual samples in light grey
        ax.plot(common_strain, interp_stress, color='grey', alpha=0.3, lw=1)

    # Calculate Mean and Standard Deviation
    master_stress = np.mean(all_interp_stress, axis=0)
    std_stress = np.std(all_interp_stress, axis=0)
    
    # Plot Master Curve
    ax.plot(common_strain, master_stress, color='red', label='MASTER CURVE (Mean)', lw=3)
    ax.fill_between(common_strain, master_stress - std_stress, master_stress + std_stress, color='red', alpha=0.1, label='Std. Deviation')
    
    ax.set_xlabel("Strain (%)")
    ax.set_ylabel("Stress (MPa)")
    ax.set_title(f"Master Curve Generation: {project_name}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
    
    # --- 6. Stats & Export ---
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("Master Yield (Mean)", f"{master_stress.max():.2f} MPa")
    with col_stat2:
        st.metric("Avg. Extrapolated Stress", f"{master_stress[-1]:.2f} MPa")
    
    # Export
    df_master = pd.DataFrame({
        'Common Strain (%)': common_strain,
        'Mean Stress (MPa)': master_stress,
        'Std Dev': std_stress
    })
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_master.to_excel(writer, index=False, sheet_name="Master Curve")
        # Add individual samples for reference
        for name, data in st.session_state.samples.items():
            pd.DataFrame({'Strain': data['strain'], 'Stress': data['stress']}).to_excel(writer, sheet_name=name[:30], index=False)
            
    st.download_button("📥 Download Master Report", output.getvalue(), f"{project_name}_Master_Analysis.xlsx")
