import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests
import re

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Tensile Suite", layout="wide")

# --- 2. Professional Header & Logo ---
logo_url = "https://raw.githubusercontent.com/12solo/Tensile-test-extrapolator/main/logo%20s.png"

col_logo, col_text = st.columns([1, 5])
with col_logo:
    try:
        st.image(logo_url, width=150)
    except:
        st.header("🔬")

with col_text:
    st.title("Solomon Tensile Suite")
    st.markdown("**Developed by Solomon** 🚀")

st.info("""
The Solomon Tensile Suite is a high-fidelity analytical framework engineered for Material Scientists and Mechanical Engineers. 
Optimized for biodegradable polymers (PBAT/PLA), it automatically detects the maximum stress point and extrapolates the drawing plateau to characterize mechanical performance even in cases of premature test termination.
""")

# --- Sidebar Link ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Tensile suite Pro")
st.sidebar.link_button(
    "Batch analyser App", 
    "https://solomon--tensile-test-batch-analysis-33vrgvcpcctqwxnuez5pci.streamlit.app/",
    use_container_width=True
)

# --- 3. Sidebar Parameters ---
st.sidebar.header("📂 Project Metadata")
project_name = st.sidebar.text_input("Project Name / Research Topic", "PBAT/PLA")
batch_id = st.sidebar.text_input("Batch ID / Sample Name", "Batch-001")

st.sidebar.header("⚙️ Extrapolation Parameters")
target_def = st.sidebar.number_input("Target Final Deformation (mm)", value=395.54, step=10.0)
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0, step=0.5)

st.sidebar.header("📏 Material Properties Setup")
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=25.0, step=1.0)
ym_start = st.sidebar.number_input("Modulus Start Elongation (%)", value=0.2, step=0.1)
ym_end = st.sidebar.number_input("Modulus End Elongation (%)", value=1.0, step=0.1)

st.sidebar.header("🎯 Yield Point Setup")
calc_yield = st.sidebar.checkbox("Calculate Yield Point", value=True)
yield_search_max = st.sidebar.number_input("Max Strain to Search (%)", value=35.0, step=5.0)

st.sidebar.header("🔍 Zoom Graph Position")
inset_x = st.sidebar.slider("Horizontal (X)", 0.0, 0.8, 0.55, 0.05)
inset_y = st.sidebar.slider("Vertical (Y)", 0.0, 0.8, 0.05, 0.05)
inset_w = st.sidebar.slider("Width", 0.2, 0.6, 0.40, 0.05)
inset_h = st.sidebar.slider("Height", 0.2, 0.6, 0.40, 0.05)

st.sidebar.header("🎛️ Advanced Settings")
apply_noise = st.sidebar.checkbox("Apply Plateau Noise", value=True)
noise_std = st.sidebar.number_input("Noise Std Dev (N)", value=0.1, step=0.05)
ref_points = st.sidebar.number_input("Slope Ref Points", value=50, step=5)

# --- 4. Robust File Uploader ---
uploaded_file = st.file_uploader("Upload Tensile Data (Excel, CSV, or TXT)", type=['csv', 'xlsx', 'xls', 'txt'])

def robust_load(file):
    ext = file.name.split('.')[-1].lower()
    if ext in ['xlsx', 'xls']:
        return pd.read_excel(file)
    
    raw_bytes = file.getvalue()
    content = raw_bytes.decode("utf-8", errors="ignore")
    lines = content.splitlines()
    
    start_row = 0
    for i, line in enumerate(lines):
        if len(re.findall(r"[-+]?\d*\.\d+|\d+", line)) >= 2:
            start_row = i
            break
    
    sep = '\t' if '\t' in lines[start_row] else (',' if ',' in lines[start_row] else r'\s+')
    df = pd.read_csv(io.StringIO("\n".join(lines[start_row:])), sep=sep, engine='python', on_bad_lines='skip')
    df.columns = [str(c).strip() for c in df.columns]
    return df

if uploaded_file is not None:
    df = robust_load(uploaded_file)
    cols = df.columns.tolist()
    
    c_a, c_b = st.columns(2)
    with c_a:
        force_col = st.selectbox("Force/Load Column", cols, index=0)
    with c_b:
        def_col = st.selectbox("Deformation/Extension Column", cols, index=1 if len(cols)>1 else 0)

    if st.button("Calculate & Generate Analysis"):
        # --- PRE-PROCESSING ---
        df[force_col] = pd.to_numeric(df[force_col], errors='coerce')
        df[def_col] = pd.to_numeric(df[def_col], errors='coerce')
        df = df.dropna(subset=[force_col, def_col])

        # --- AUTO-DETECTION OF PEAK STRESS ---
        idx_max = df[force_col].idxmax()
        df_trimmed = df.loc[:idx_max].copy()

        # --- EXTRAPOLATION LOGIC ---
        last_n = df_trimmed.tail(ref_points)
        slope, intercept = np.polyfit(last_n[def_col].values, last_n[force_col].values, 1)
        
        D_stop = df_trimmed[def_col].iloc[-1] 
        L_stop = df_trimmed[force_col].iloc[-1]
        avg_step = np.mean(np.diff(df_trimmed[def_col].tail(10).values))
        
        D_new = np.arange(D_stop + avg_step, target_def + avg_step, avg_step)
        if len(D_new) > 0 and D_new[-1] > target_def: D_new[-1] = target_def
        
        np.random.seed(42)
        noise = np.random.normal(0, noise_std, len(D_new)) if apply_noise else 0
        L_new = L_stop + slope * (D_new - D_stop) + noise
        
        # Combine Data
        df_orig = pd.DataFrame({'Force (N)': df_trimmed[force_col], 'Deformation (mm)': df_trimmed[def_col], 'Type': 'Original'})
        df_ext = pd.DataFrame({'Force (N)': L_new, 'Deformation (mm)': D_new, 'Type': 'Extrapolated'})
        df_combined = pd.concat([df_orig, df_ext], ignore_index=True)
        
        df_combined['Stress (MPa)'] = df_combined['Force (N)'] / area
        df_combined['Strain (%)'] = (df_combined['Deformation (mm)'] / gauge_length) * 100
        
        # --- CONSTITUTIVE CALCULATIONS WITH SAFETY CHECK ---
        mask_ym = (df_combined['Strain (%)'] >= ym_start) & (df_combined['Strain (%)'] <= ym_end)
        
        if mask_ym.any():
            E, inter_ym = np.polyfit(df_combined.loc[mask_ym, 'Deformation (mm)']/gauge_length, df_combined.loc[mask_ym, 'Stress (MPa)'], 1)
            
            y_mask = df_combined['Strain (%)'] <= yield_search_max
            y_idx = df_combined.loc[y_mask, 'Stress (MPa)'].idxmax()
            y_stress, y_strain = df_combined.loc[y_idx, 'Stress (MPa)'], df_combined.loc[y_idx, 'Strain (%)']

            try: work_j = np.trapezoid(df_combined['Force (N)'], df_combined['Deformation (mm)']) / 1000.0
            except: work_j = np.trapz(df_combined['Force (N)'], df_combined['Deformation (mm)']) / 1000.0

            # --- DASHBOARD METRICS ---
            st.success(f"Analysis for {batch_id} Complete!")
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Modulus (E)", f"{E:.1f} MPa")
            m2.metric("Yield Stress", f"{y_stress:.2f} MPa")
            m3.metric("Yield Strain", f"{y_strain:.2f} %")
            m4.metric("Stress @ Peak", f"{df_combined['Stress (MPa)'].iloc[idx_max]:.2f} MPa")
            m5.metric("Strain @ Break", f"{df_combined['Strain (%)'].iloc[-1]:.1f} %")
            m6.metric("Work Done", f"{work_j:.2f} J")

            # --- PLOTTING WITH DISTINCT COLORS ---
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # 1. Original Data - Deep Blue
            ax.plot(df_combined.loc[df_combined['Type']=='Original', 'Strain (%)'], 
                    df_combined.loc[df_combined['Type']=='Original', 'Stress (MPa)'], 
                    label='Original (to Peak)', color='#1f77b4', lw=2.5)
            
            # 2. Extrapolated Data - Vibrant Orange (Dashed)
            ax.plot(df_combined.loc[df_combined['Type']=='Extrapolated', 'Strain (%)'], 
                    df_combined.loc[df_combined['Type']=='Extrapolated', 'Stress (MPa)'], 
                    label='Extrapolated Plateau', color='#ff7f0e', ls='--', alpha=0.8, lw=2)
            
            # 3. Elastic Fit - Purple (Dotted)
            xfv = np.linspace(0, ym_end/100 * 1.5, 50)
            yfv = E * xfv + inter_ym
            ax.plot(xfv * 100, yfv, color='#9467bd', ls=':', label='Elastic Fit', lw=2)
            
            # 4. Max Stress - Red Star
            peak_strain = df_combined['Strain (%)'].iloc[idx_max]
            peak_stress = df_combined['Stress (MPa)'].iloc[idx_max]
            ax.plot(peak_strain, peak_stress, '*', color='#d62728', markersize=14, label='Max Stress', zorder=5)
            ax.axvline(x=peak_strain, color='gray', linestyle='--', alpha=0.4, lw=1)
            
            # 5. Yield Point - Teal Green Circle
            if calc_yield: 
                ax.plot(y_strain, y_stress, 'o', color='#2ca02c', markersize=8, label='Yield Point', markeredgecolor='black', zorder=6)
            
            ax.set_xlabel('Strain (%)', fontweight='bold')
            ax.set_ylabel('Stress (MPa)', fontweight='bold')
            ax.legend(loc='lower right', frameon=True, shadow=True)
            ax.grid(True, linestyle='--', alpha=0.5)
            
            # Inset Zoom with matching colors
            axins = ax.inset_axes([inset_x, inset_y, inset_w, inset_h])
            axins.plot(df_combined['Strain (%)'].iloc[:len(df_orig)], df_combined['Stress (MPa)'].iloc[:len(df_orig)], color='#1f77b4')
            axins.plot(xfv * 100, yfv, color='#9467bd', ls=':')
            if calc_yield:
                axins.plot(y_strain, y_stress, 'o', color='#2ca02c', markersize=6, markeredgecolor='black')
                
            z_lim = max(ym_end + 1.5, y_strain + 1.5 if calc_yield else 0)
            axins.set_xlim(0, z_lim)
            axins.set_ylim(0, df_combined.loc[df_combined['Strain (%)'] <= z_lim, 'Stress (MPa)'].max() * 1.3)
            ax.indicate_inset_zoom(axins, edgecolor="black")
            st.pyplot(fig)

            # --- EXPORT ---
            summary_data = {
                "Property": ["Project", "Batch", "Modulus (E)", "Yield Stress", "Yield Strain", "Peak Stress", "Strain @ Break", "Work Done"],
                "Value": [project_name, batch_id, f"{E:.2f}", f"{y_stress:.2f}", f"{y_strain:.2f}", f"{peak_stress:.2f}", f"{df_combined['Strain (%)'].iloc[-1]:.2f}", f"{work_j:.4f}"],
                "Unit": ["-", "-", "MPa", "MPa", "%", "MPa", "%", "J"]
            }
            df_summary = pd.DataFrame(summary_data)

            img_data = io.BytesIO()
            fig.savefig(img_data, format='png', dpi=100)
            img_data.seek(0)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_combined.to_excel(writer, index=False, sheet_name="Full Dataset")
                workbook = writer.book
                worksheet = workbook.add_worksheet("Summary Report")
                df_summary.to_excel(writer, index=False, sheet_name="Summary Report", startrow=1, startcol=1)
                worksheet.insert_image('F2', 'plot.png', {'image_data': img_data, 'x_scale': 0.7, 'y_scale': 0.7})

            st.download_button(
                label=f"📥 Download Report for {batch_id}", 
                data=output.getvalue(), 
                file_name=f"{batch_id}_Tensile_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.subheader("📋 Data Preview Table")
            st.dataframe(df_combined[['Strain (%)', 'Stress (MPa)', 'Force (N)', 'Type']], height=300)
        
        else:
            st.error(f"⚠️ **Range Error:** No data points found between {ym_start}% and {ym_end}% strain. Please check your Gauge Length or expand the Modulus Elongation range in the sidebar.")
