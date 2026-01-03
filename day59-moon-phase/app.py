import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import streamlit.components.v1 as components
from skyfield.api import load, wgs84
import pandas as pd

# --- 1. ページ設定とデータ読み込み ---
st.set_page_config(page_title="Sky Dome Simulator", layout="wide")
st.markdown("#### 🌙 月齢と太陽・月の軌道シミュレーター")

@st.cache_resource
def load_data():
    # 天体暦データの読み込み
    eph = load('de421.bsp')
    ts = load.timescale()
    return eph, ts

eph, ts = load_data()

# --- 2. サイドバー設定（日付選択） ---
st.sidebar.header("観測設定")
date_selection = st.sidebar.date_input("日付を選択", value=None) 
hiroshima = wgs84.latlon(34.3853, 132.4553)
observer = eph['earth'] + hiroshima

# 観測地点を表示
st.sidebar.markdown("### 📍 観測地点")
st.sidebar.text("広島市")
st.sidebar.text("緯度: 34.3853°")
st.sidebar.text("経度: 132.4553°")

if date_selection:
    y, m, d = date_selection.year, date_selection.month, date_selection.day
    # 日本時間0時のためのUTC変換（前日15時）
    t_list = ts.utc(y, m, d-1, range(15, 15 + 24))
    
    # --- 3. 天体計算 ---
    sun, moon = eph['sun'], eph['moon']
    sun_obs = observer.at(t_list).observe(sun).apparent()
    moon_obs = observer.at(t_list).observe(moon).apparent()
    
    sun_altaz = sun_obs.altaz()
    moon_altaz = moon_obs.altaz()

    # --- 4. 描画のセットアップ (2画面構成) ---
    # col1: 黄道面俯瞰図, col2: 広島の空3D
    fig = plt.figure(figsize=(14, 7))
    
    # --- 左側: 黄道面俯瞰 (2D) ---
    ax_orbit = fig.add_subplot(121)
    ax_orbit.set_aspect('equal')
    ax_orbit.set_facecolor('#0E1117')
    ax_orbit.set_title("Ecliptic Plane View", color='white', pad=20)
    
    # 地球(中心)と太陽方向の矢印
    ax_orbit.plot(0, 0, 'blue', marker='o', markersize=15, label='Earth')
    ax_orbit.quiver(0, 0, 1.2, 0, color='orange', angles='xy', scale_units='xy', scale=1)
    ax_orbit.text(1.3, 0, "Sun", color='orange', fontweight='bold')
    
    # 公転軌道の円
    orbit_circle = plt.Circle((0, 0), 1.0, color='white', fill=False, alpha=0.2, linestyle='--')
    ax_orbit.add_artist(orbit_circle)
    
    # 月のプロット（宇宙側）
    moon_orbit_point, = ax_orbit.plot([], [], 'ko', markersize=12, markeredgecolor='white', label='Moon')
    ax_orbit.set_xlim(-1.5, 1.5); ax_orbit.set_ylim(-1.5, 1.5)
    ax_orbit.axis('off')

    # --- 右側: 広島の空 (3D) ---
    ax_3d = fig.add_subplot(122, projection='3d')
    ax_3d.set_title("Hiroshima Sky Dome", pad=20)
    
    # 球体と地平線の描画
    u, v = np.mgrid[0:2*np.pi:30j, 0:np.pi:30j] # 全球体
    ax_3d.plot_wireframe(np.cos(u)*np.sin(v), np.sin(u)*np.sin(v), np.cos(v), color="gray", alpha=0.05)
    theta = np.linspace(0, 2*np.pi, 100)
    ax_3d.plot(np.cos(theta), np.sin(theta), 0, color='blue', lw=1, alpha=0.3)

    # 太陽・月の点と軌道
    sun_point, = ax_3d.plot([], [], [], 'yo', markersize=12, label='Sun')
    sun_path,  = ax_3d.plot([], [], [], 'orange', alpha=0.5, lw=2)
    moon_point, = ax_3d.plot([], [], [], 'ko', markersize=10, markeredgecolor='gray', label='Moon')
    moon_path,  = ax_3d.plot([], [], [], 'gray', alpha=0.5, lw=1)

    ax_3d.set_xlim(-1, 1); ax_3d.set_ylim(-1, 1); ax_3d.set_zlim(-1, 1)
    ax_3d.view_init(elev=20, azim=45)
    ax_3d.legend(loc='upper right')

    # 座標変換関数
    def get_xyz(alt_deg, az_deg):
        alt_r, az_r = np.radians(alt_deg), np.radians(az_deg)
        return np.cos(alt_r)*np.sin(az_r), np.cos(alt_r)*np.cos(az_r), np.sin(alt_r)

    s_coords = [get_xyz(alt, az) for alt, az in zip(sun_altaz[0].degrees, sun_altaz[1].degrees)]
    m_coords = [get_xyz(alt, az) for alt, az in zip(moon_altaz[0].degrees, moon_altaz[1].degrees)]

    # --- 5. アニメーション更新関数 ---
    def update(frame):
        # A. 宇宙俯瞰図の更新 (太陽と月の黄経差を利用)
        # Skyfieldの月齢角を直接取得
        t = t_list[frame]
        m_lon = eph['moon'].at(t).observe(eph['sun']).apparent().separation_from(eph['earth'].at(t).observe(eph['moon']).apparent())
        angle_rad = np.radians(m_lon.degrees)
        moon_orbit_point.set_data([np.cos(angle_rad)], [np.sin(angle_rad)])
        
        # B. 3Dドームの更新
        sx, sy, sz = s_coords[frame]
        sun_point.set_data([sx], [sy])
        sun_point.set_3d_properties([sz])
        sun_path.set_data([c[0] for c in s_coords[:frame+1]], [c[1] for c in s_coords[:frame+1]])
        sun_path.set_3d_properties([c[2] for c in s_coords[:frame+1]])
        
        mx, my, mz = m_coords[frame]
        moon_point.set_data([mx], [my])
        moon_point.set_3d_properties([mz])
        moon_path.set_data([c[0] for c in m_coords[:frame+1]], [c[1] for c in m_coords[:frame+1]])
        moon_path.set_3d_properties([c[2] for c in m_coords[:frame+1]])
        
        fig.suptitle(f"{date_selection} {frame:02d}:00 JST", fontsize=16)
        return sun_point, sun_path, moon_point, moon_path, moon_orbit_point

    ani = FuncAnimation(fig, update, frames=24, interval=150, blit=True)
    
    # 表示
    components.html(ani.to_jshtml(), height=800)
    
    # サイドバーに月齢を表示
    t_noon = ts.utc(y, m, d, 3)  # 日本時間正午（UTC3時）
    s_noon = observer.at(t_noon).observe(sun).apparent()
    m_noon = observer.at(t_noon).observe(moon).apparent()
    sep_noon = m_noon.separation_from(s_noon).degrees
    # 黄経（longitude）を直接取得して差を計算する、より正確な方法
    _, s_lon, _ = s_noon.ecliptic_latlon()
    _, m_lon, _ = m_noon.ecliptic_latlon()
    # 月が太陽からどれだけ進んでいるか (0〜360度)
    phase_angle = (m_lon.degrees - s_lon.degrees) % 360
    moon_age = (phase_angle / 360 * 29.53)
    st.sidebar.write(f"月齢（参考）: {moon_age:.1f} 日")

    # サイドバーに月齢の目安を表示
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🌗 月齢の目安")
    phase_data = {
    "状態": ["新月（朔）", "上弦", "満月（望）", "下弦"],
    "黄経差": ["0°", "90°", "180°", "270°"],
    "月齢": ["0.0", "約 7.4", "約 14.8", "約 22.1"]
    }
    df_phase = pd.DataFrame(phase_data)
    st.sidebar.table(df_phase) # 表として表示                    
    