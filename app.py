import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="Tensile Data Extrapolator", layout="wide")

# --- Developer Credit ---
st.title("📈 Tensile Test Extrapolator")
st.markdown("**Developed by Solomon** 🚀")
st.markdown("Upload your test data, set the parameters, calculate mechanical properties, and download the dataset.")

# --- Sidebar for parameters ---
st.sidebar.header("⚙️ Extrapolation Parameters")
target_def = st.sidebar.number_input("Target Final Deformation (mm)", value=395.54, step=10.0)
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0, step=0.5)

st.sidebar.header("📏 Material Properties Setup")
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0, step=1.0)
ym_start = st.sidebar.number_input("Modulus Start Elongation (%)", value=0.2, step=0.1)
ym_end = st.sidebar.number_input("Modulus End Elongation (%)", value=1.0, step=0.1)

# --- Yield Point Setup ---
st.sidebar.header("🎯 Yield Point Setup")
calc_yield = st.sidebar.checkbox("Calculate Yield Point", value=True)
yield_search_max = st.sidebar.number_input("Max Strain to Search for Yield (%)", value=25.0, step=5.0)

# --- Zoom Box Controls ---
st.sidebar.header("🔍 Zoom Graph Position")
st.sidebar.markdown("Move the box to avoid overlapping the curve.")
inset_x = st.sidebar.slider("Horizontal Position (X)", min_value=0.0, max_value=0.8, value=0.55, step=0.05)
inset_y = st.sidebar.slider("Vertical Position (Y)", min_value=0.0, max_value=0.8, value=0.05, step=0.05)
inset_w = st.sidebar.slider("Box Width", min_value=0.2, max_value=0.6, value=0.40, step=0.05)
inset_h = st.sidebar.slider("Box Height", min_value=0.2, max_value=0.6, value=0.40, step=0.05)

st.sidebar.header("🎛️ Advanced Settings")
noise_std = st.sidebar.number_input("Noise Standard Deviation (N)", value=0.1, step=0.05)
ref_points = st.sidebar.number_input("Points for Reference Trend (Slope)", value=50, step=5)

# --- File uploader ---
uploaded_file = st.file_uploader("Upload Tensile Test Data (Excel or CSV)", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    st.subheader("1. Column Selection")
    cols = df.columns.tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        force_col = st.selectbox("Select Force Column (N)", cols, index=0)
    with col2:
        def_col = st.selectbox("Select Deformation Column (mm)", cols, index=1 if len(cols)>1 else 0)

    st.subheader("2. Results & Extrapolation")
    
    if st.button("Calculate & Generate Extrapolation"):
        last_n = df.tail(ref_points)
        x_last = last_n[def_col].values
        y_last = last_n[force_col].values
        
        slope, intercept = np.polyfit(x_last, y_last, 1)
        
        D_stop = df[def_col].iloc[-1]
        L_stop = df[force_col].iloc[-1]
        
        avg_step = np.mean(np.diff(df[def_col].tail(10).values))
        
        if target_def > D_stop:
            D_new = np.arange(D_stop + avg_step, target_def + avg_step, avg_step)
            if D_new[-1] > target_def:
                D_new[-1] = target_def
            
            np.random.seed(42) 
            L_new = L_stop + slope * (D_new - D_stop) + np.random.normal(0, noise_std, len(D_new))
            
            df_ext = pd.DataFrame({'Force (N)': L_new, 'Deformation (mm)': D_new})
            df_orig = pd.DataFrame({'Force (N)': df[force_col], 'Deformation (mm)': df[def_col]})
            df_combined = pd.concat([df_orig, df_ext], ignore_index=True)
            
            df_combined['Stress (MPa)'] = df_combined['Force (N)'] / area
            df_combined['Strain (mm/mm)'] = df_combined['Deformation (mm)'] / gauge_length
            df_combined['Strain (%)'] = df_combined['Strain (mm/mm)'] * 100
            
            # --- MODULUS CALCULATION ---
            mask = (df_combined['Strain (%)'] >= ym_start) & (df_combined['Strain (%)'] <= ym_end)
            x_ym = df_combined.loc[mask, 'Strain (mm/mm)'].values
            y_ym = df_combined.loc[mask, 'Stress (MPa)'].values
            
            if len(x_ym) > 1:
                youngs_modulus, intercept_ym = np.polyfit(x_ym, y_ym, 1)
            else:
                youngs_modulus = 0.0 
            
            # --- YIELD POINT ---
            yield_stress, yield_strain = 0.0, 0.0
            if calc_yield:
                yield_mask = df_combined['Strain (%)'] <= yield_search_max
                yield_idx = df_combined.loc[yield_mask, 'Stress (MPa)'].idxmax()
                yield_stress = df_combined.loc[yield_idx, 'Stress (MPa)']
                yield_strain = df_combined.loc[yield_idx, 'Strain (%)']

            # --- BREAK PROPERTIES ---
            elong_break = df_combined['Strain (%)'].iloc[-1]
            stress_break = df_combined['Stress (MPa)'].iloc[-1]
            
            # Handle trapz/trapezoid for different NumPy versions
            try:
                work_j = np.trapezoid(df_combined['Force (N)'], df_combined['Deformation (mm)']) / 1000.0
            except AttributeError:
                work_j = np.trapz(df_combined['Force (N)'], df_combined['Deformation (mm)']) / 1000.0
            
            # --- DASHBOARD ---
            st.success("Calculations Complete!")
            c1, c2, c3 = st.columns(3)
            c1.metric("Young's Modulus", f"{youngs_modulus:.2f} MPa")
            c2.metric("Yield Stress", f"{yield_stress:.2f} MPa")
            c3.metric("Elongation @ Yield", f"{yield_strain:.2f} %")
            
            c4, c5, c6 = st.columns(3)
            c4.metric("Stress @ Break", f"{stress_break:.2f} MPa")
            c5.metric("Elongation @ Break", f"{elong_break:.2f} %")
            c6.metric("Work Done", f"{work_j:.2f} J")
            
            # --- PLOTTING ---
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df_combined['Strain (%)'].iloc[:len(df_orig)], df_combined['Stress (MPa)'].iloc[:len(df_orig)], label='Original Data', color='blue')
            ax.plot(df_combined['Strain (%)'].iloc[len(df_orig)-1:], df_combined['Stress (MPa)'].iloc[len(df_orig)-1:], label='Extrapolation', color='red', alpha=0.7)
            
            if len(x_ym) > 1:
                xfv = np.linspace(0, ym_end/100 * 1.5, 50)
                yfv = youngs_modulus * xfv + intercept_ym
                ax.plot(xfv * 100, yfv, color='green', linestyle='--', label='Elastic Fit')
            
            if calc_yield:
                ax.plot(yield_strain, yield_stress, 'o', color='orange', label='Yield Point')

            ax.set_xlabel('Strain (%)')
            ax.set_ylabel('Stress (MPa)')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3)
            
            # Inset
            axins = ax.inset_axes([inset_x, inset_y, inset_w, inset_h])
            axins.plot(df_combined['Strain (%)'].iloc[:len(df_orig)], df_combined['Stress (MPa)'].iloc[:len(df_orig)], color='blue')
            if len(x_ym) > 1:
                axins.plot(xfv * 100, yfv, color='green', linestyle='--')
            
            z_max = max(ym_end + 1.0, yield_strain + 1.0 if calc_yield else 0)
            axins.set_xlim(0, z_max)
            axins.set_ylim(0, df_combined.loc[df_combined['Strain (%)'] <= z_max, 'Stress (MPa)'].max() * 1.2)
            ax.indicate_inset_zoom(axins, edgecolor="black")
            
            st.pyplot(fig)
            
            # --- EXPORT ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_combined.to_excel(writer, index=False)
            st.download_button("📥 Download Excel", output.getvalue(), "Extended_Data_Solomon.xlsx")
        else:
            st.error("Target deformation must be higher than sample stop point.")