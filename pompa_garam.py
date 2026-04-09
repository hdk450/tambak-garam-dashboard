import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import math

st.set_page_config(page_title="Tambak v4 - Luas Auto", layout="wide")

st.title("🧂 Dashboard Tambak Garam **v4.0**")
st.markdown("**Volume = Luas (Ha) × Kedalaman • Q m³/jam • Velocity • Porosity**")

# Sidebar: Input Intuitif
st.sidebar.header("🌾 **Ukuran Tambak**")
luas_ha = st.sidebar.number_input("**Luas Lahan** (Ha)", value=283.3, step=1.0)
kedalaman_m = st.sidebar.number_input("**Kedalaman Air** (m)", value=1.0, min_value=0.1, step=0.1)

# AUTO-HITUNG VOLUME
V_target = luas_ha * 10000 * kedalaman_m  # Ha → m² → m³
st.sidebar.metric("**Volume Target**", f"{V_target:,.0f} m³")

st.sidebar.header("💧 **Pompa & Pipa**")
Q_m3h = st.sidebar.number_input("**Debit** (m³/jam)", value=997200, step=5000)
velocity_mps = st.sidebar.slider("**Velocity** (m/s)", 0.3, 3.0, 0.62)
diameter_m = st.sidebar.number_input("Diameter Pipa (m)", value=2.0, step=0.1)

st.sidebar.header("🏺 **Tanah & Cuaca**")
porosity_pct = st.sidebar.slider("Porosity (%)", 20, 60, 40)
field_cap_pct = st.sidebar.slider("Field Capacity (%)", 60, 90, 75)
evap_mmharian = st.sidebar.number_input("Penguapan (mm/hari)", value=3.0, step=0.5)

# KONVERSI & DERIVATIF
Q_m3s = Q_m3h / 3600
A_luas_m2 = luas_ha * 10000
evap_daily_m = evap_mmharian / 1000
field_cap = porosity_pct / 100 * field_cap_pct / 100
V_eff = V_target / field_cap

area_pipa = math.pi * (diameter_m/2)**2
Q_from_pipe = velocity_mps * area_pipa

# DASHBOARD METRIK
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1: st.metric("🌾 Luas", f"{luas_ha:.1f} Ha")
with col2: st.metric("📏 Kedalaman", f"{kedalaman_m} m")
with col3: st.metric("💦 Volume", f"{V_target:,.0f} m³")
with col4: st.metric("⏱️ Waktu Dasar", f"{V_target/Q_m3s/3600:.1f} jam")
with col5: st.metric("🏺 +Porosity", f"{V_eff/Q_m3s/3600:.1f} jam")
with col6: st.metric("💨 Velocity", f"{velocity_mps:.2f} m/s")

st.markdown("---")

# SIMULASI
if st.button("🎯 **Simulasi Pengisian**", type="primary"):
    dt_h = 0.25
    dt = dt_h * 3600
    time_sec = np.arange(0, V_eff/Q_m3s * 1.5 * 3600, dt)
    
    vol_filled = np.zeros(len(time_sec))
    evap_total = np.zeros(len(time_sec))
    
    for i, t in enumerate(time_sec):
        inflow = Q_m3s * dt
        fill_ratio = vol_filled[max(0,i-1)] / V_target if i>0 else 0
        evap_step = (evap_daily_m / 24) * A_luas_m2 * fill_ratio * (dt/3600)
        net = inflow - evap_step
        vol_filled[i] = min(vol_filled[max(0,i-1)] + net, V_target)
        evap_total[i] = evap_step
        if vol_filled[i] >= V_target: 
            break   # ← Pastikan ini align dengan for
    
    # Pastikan df_result di luar loop
    df_result = pd.DataFrame({
        'Waktu (jam)': time_sec[:i+1]/3600,
        'Volume Terisi (m³)': vol_filled[:i+1],
        'Evaporasi (m³)': np.cumsum(evap_total[:i+1]),
        'Q Efektif (m³/jam)': Q_m3h * (1 - np.cumsum(evap_total[:i+1])/np.cumsum([Q_m3s*dt]*(i+1)))
    })
    
    # TABS
    tab1, tab2 = st.tabs(["📈 Visualisasi", "📊 Data & Export"])
    
    with tab1:
        fig = px.line(df_result, x='Waktu (jam)', y='Volume Terisi (m³)',
                     title=f"Target {V_target:,.0f} m³ tercapai dalam {df_result['Waktu (jam)'].iloc[-1]:.1f} jam")
        fig.add_hline(y=V_target, line_dash="dash", line_color="green", 
                     annotation_text=f"Target {luas_ha:.1f}Ha × {kedalaman_m}m")
        fig.add_scatter(x=df_result['Waktu (jam)'], y=df_result['Evaporasi (m³)'],
                       name='Evaporasi', line=dict(color='orange', dash='dot'))
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary Cards
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1: st.metric("⏰ Total Waktu", f"{df_result['Waktu (jam)'].iloc[-1]:.1f} jam")
        with col_s2: st.metric("💧 Total Evap", f"{df_result['Evaporasi (m³)'].iloc[-1]:.0f} m³")
        with col_s3: st.metric("⚡ Efisiensi", f"{V_target/(V_target+df_result['Evaporasi (m³)'].iloc[-1])*100:.1f}%")
        with col_s4: st.metric("📈 Q Akhir", f"{df_result['Q Efektif (m³/jam)'].iloc[-1]:.0f} m³/jam")
    
    with tab2:
        st.dataframe(df_result.round(0), height=400, use_container_width=True)
        
        csv_bytes = df_result.round(0).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="💾 Download Simulasi CSV",
            data=csv_bytes,
            file_name=f"tambak_{luas_ha:.0f}Ha_{kedalaman_m}m_Q{Q_m3h/1000:.0f}k.csv",
            mime="text/csv"
        )

# INFO PANEL
with st.expander("📋 **Spesifikasi Input Tambak Garam**"):
    st.write("""
    | Parameter | Nilai Tipikal | Satuan |
    |-----------|---------------|--------|
    | **Luas** | 50-500 | Ha |
    | **Kedalaman** | 0.8-1.5 | m |
    | **Porosity** | 30-50% | - |
    | **Penguapan** | 3-8 mm/hari | tropis |
    | **Velocity** | 0.6-1.5 | m/s |
    """)

st.markdown("---")
st.caption("**v4.0 • Volume Auto Luas×Kedalaman • Siap Thesis & Lapangan** 🧲")
