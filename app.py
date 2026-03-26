import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests

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
    st.title("Solomon Tensile Suite v1.9")
    st.markdown("**Developed by Solomon** 🚀")

st.info("""
The Solomon Tensile Suite is a high-fidelity analytical framework engineered for Material Scientists and Mechanical Engineers. 
While optimized for biodegradable polymers—specifically PBAT and PBAT/PLA blends—it provides a robust solution for the "premature termination" problem common in high-elongation testing. 
By utilizing advanced linear extrapolation of the drawing plateau, the suite bridges the gap between empirical laboratory data and theoretical failure points, ensuring a comprehensive characterization of mechanical performance
""")

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

# --- 4. File Uploader ---
uploaded_file = st.file_uploader("Upload Tensile Data (Excel or CSV)", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    cols = df.columns.tolist()
    
    c_a, c_b = st.columns(2)
    with c_a:
        force_col = st.selectbox("Force Column (N)", cols, index=0)
    with c_b:
        def_col = st.selectbox("Deformation Column (mm)", cols, index=1 if len(cols)>1 else 0)

    if st.button("Calculate & Generate Analysis"):
        # --- CALCULATION LOGIC ---
        last_n = df.tail(ref_points)
        slope, intercept = np.polyfit(last_n[def_col].values, last_n[force_col].values, 1)
        D_stop, L_stop = df[def_col].iloc[-1], df[force_col].iloc[-1]
        avg_step = np.mean(np.diff(df[def_col].tail(10).values))
        
        D_new = np.arange(D_stop + avg_step, target_def + avg_step, avg_step)
        if len(D_new) > 0 and D_new[-1] > target_def: D_new[-1] = target_def
        
        np.random.seed(42)
        noise = np.random.normal(0, noise_std, len(D_new)) if apply_noise else 0
        L_new = L_stop + slope * (D_new - D_stop) + noise
        
        df_orig = pd.DataFrame({'Force (N)': df[force_col], 'Deformation (mm)': df[def_col], 'Type': 'Original'})
        df_ext = pd.DataFrame({'Force (N)': L_new, 'Deformation (mm)': D_new, 'Type': 'Extrapolated'})
        df_combined = pd.concat([df_orig, df_ext], ignore_index=True)
        df_combined['Stress (MPa)'] = df_combined['Force (N)'] / area
        df_combined['Strain (%)'] = (df_combined['Deformation (mm)'] / gauge_length) * 100
        
        # Modulus Fit
        mask_ym = (df_combined['Strain (%)'] >= ym_start) & (df_combined['Strain (%)'] <= ym_end)
        E, inter_ym = np.polyfit(df_combined.loc[mask_ym, 'Deformation (mm)']/gauge_length, df_combined.loc[mask_ym, 'Stress (MPa)'], 1)
        
        # Yield Point
        y_mask = df_combined['Strain (%)'] <= yield_search_max
        y_idx = df_combined.loc[y_mask, 'Stress (MPa)'].idxmax()
        y_stress, y_strain = df_combined.loc[y_idx, 'Stress (MPa)'], df_combined.loc[y_idx, 'Strain (%)']

        # Energy
        try: work_j = np.trapezoid(df_combined['Force (N)'], df_combined['Deformation (mm)']) / 1000.0
        except: work_j = np.trapz(df_combined['Force (N)'], df_combined['Deformation (mm)']) / 1000.0

        # --- DASHBOARD ---
        st.success(f"Analysis for {batch_id} Complete!")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Modulus (E)", f"{E:.1f} MPa")
        m2.metric("Yield Stress", f"{y_stress:.2f} MPa")
        m3.metric("Yield Strain", f"{y_strain:.2f} %")
        m4.metric("Stress @ Break", f"{df_combined['Stress (MPa)'].iloc[-1]:.2f} MPa")
        m5.metric("Strain @ Break", f"{df_combined['Strain (%)'].iloc[-1]:.1f} %")
        m6.metric("Work Done", f"{work_j:.2f} J")

        # --- PLOTTING ---
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df_combined.loc[df_combined['Type']=='Original', 'Strain (%)'], df_combined.loc[df_combined['Type']=='Original', 'Stress (MPa)'], label='Original', color='blue', lw=2)
        ax.plot(df_combined.loc[df_combined['Type']=='Extrapolated', 'Strain (%)'], df_combined.loc[df_combined['Type']=='Extrapolated', 'Stress (MPa)'], label='Extrapolated', color='red', ls='--', alpha=0.7)
        xfv = np.linspace(0, ym_end/100 * 1.5, 50)
        yfv = E * xfv + inter_ym
        ax.plot(xfv * 100, yfv, color='green', ls=':', label='Elastic Fit')
        if calc_yield: ax.plot(y_strain, y_stress, 'o', color='orange', label='Yield Point')
        ax.set_xlabel('Strain (%)'); ax.set_ylabel('Stress (MPa)'); ax.legend(loc='lower right'); ax.grid(True, alpha=0.3)
        
        # Inset Zoom
        axins = ax.inset_axes([inset_x, inset_y, inset_w, inset_h])
        axins.plot(df_combined['Strain (%)'].iloc[:len(df_orig)], df_combined['Stress (MPa)'].iloc[:len(df_orig)], color='blue')
        axins.plot(xfv * 100, yfv, color='green', ls=':')
        z_lim = max(ym_end + 1.5, y_strain + 1.5 if calc_yield else 0)
        axins.set_xlim(0, z_lim); axins.set_ylim(0, df_combined.loc[df_combined['Strain (%)'] <= z_lim, 'Stress (MPa)'].max() * 1.3)
        ax.indicate_inset_zoom(axins, edgecolor="black")
        st.pyplot(fig)

        # --- ADVANCED EXPORT SECTION ---
        summary_data = {
            "Property": ["Project Name", "Batch ID", "Young's Modulus (E)", "Yield Stress", "Yield Strain", "Stress @ Break", "Strain @ Break", "Work Done"],
            "Value": [project_name, batch_id, f"{E:.2f}", f"{y_stress:.2f}", f"{y_strain:.2f}", f"{df_combined['Stress (MPa)'].iloc[-1]:.2f}", f"{df_combined['Strain (%)'].iloc[-1]:.2f}", f"{work_j:.4f}"],
            "Unit": ["-", "-", "MPa", "MPa", "%", "MPa", "%", "J"]
        }
        df_summary = pd.DataFrame(summary_data)

        # Capture Graph
        img_data = io.BytesIO()
        fig.savefig(img_data, format='png', dpi=100)
        img_data.seek(0)

        # Capture Logo
        logo_data = io.BytesIO()
        try:
            r = requests.get(logo_url)
            logo_data.write(r.content); logo_data.seek(0)
            has_logo = True
        except: has_logo = False

        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_combined.to_excel(writer, index=False, sheet_name="Full Dataset")
                workbook  = writer.book
                worksheet = workbook.add_worksheet("Summary Report")
                writer.sheets["Summary Report"] = worksheet
                
                # Branding
                if has_logo:
                    worksheet.insert_image('B1', 'logo.png', {'image_data': logo_data, 'x_scale': 0.05, 'y_scale': 0.05})
                
                header_fmt = workbook.add_format({'bold': 1, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'fg_color': '#D7E4BC'})
                worksheet.merge_range('B5:D5', 'Mechanical Analysis Summary', header_fmt)
                
                # Write Summary starting Row 6
                df_summary.to_excel(writer, index=False, sheet_name="Summary Report", startrow=5, startcol=1)
                
                # Insert Plot
                worksheet.insert_image('F6', 'plot.png', {'image_data': img_data, 'x_scale': 0.8, 'y_scale': 0.8})

            st.download_button(
                label=f"📥 Download Report for {batch_id}", 
                data=output.getvalue(), 
                file_name=f"{batch_id}_Tensile_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Excel Export Error: Ensure 'xlsxwriter' is in requirements.txt. Details: {e}")

        # Table Preview
        st.subheader("📋 Data Preview Table")
        st.dataframe(df_combined[['Strain (%)', 'Stress (MPa)', 'Force (N)', 'Type']], height=300)
