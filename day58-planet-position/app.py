import streamlit as st
from skyfield.api import load, wgs84
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, timezone
import numpy as np

st.set_page_config(page_title="惑星の高度グラフ", page_icon="📊", layout="wide")

st.title("📊 惑星の位置可視化アプリ")
st.markdown("選択した惑星の24時間の動きを様々な視点で可視化します")
st.markdown("---")

# サイドバーで設定
st.sidebar.header("⚙️ 設定")
st.sidebar.markdown("### 🪐 観測対象")

planet_names = {
    "水星 (Mercury)": "mercury",
    "金星 (Venus)": "venus",
    "火星 (Mars)": "mars",
    "木星 (Jupiter)": "jupiter barycenter",
    "土星 (Saturn)": "saturn barycenter"
}

selected_display_name = st.sidebar.selectbox(
    "惑星を選択",
    list(planet_names.keys())
)

selected_planet = planet_names[selected_display_name]

# データ準備
@st.cache_resource
def load_ephemeris():
    return load('de421.bsp')

@st.cache_resource
def load_timescale():
    return load.timescale()

planets = load_ephemeris()
earth = planets['earth']
ts = load_timescale()

# 観測地点を設定（広島）
st.sidebar.markdown("### 📍 観測地点")
st.sidebar.text("広島市")
st.sidebar.text("緯度: 34.3853°")
st.sidebar.text("経度: 132.4553°")

hiroshima = earth + wgs84.latlon(34.3853, 132.4553)

# 日本時間（JST = UTC+9）
JST = timezone(timedelta(hours=9))

# 今日の0時から24時間分のデータ（日本時間）
now = datetime.now(JST)
start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=JST)
times = [start + timedelta(hours=i) for i in range(25)]

# データ計算
@st.cache_data
def calculate_planet_data(planet_name, lat, lon, date_str):
    planets = load_ephemeris()
    earth = planets['earth']
    ts = load_timescale()
    location = earth + wgs84.latlon(lat, lon)
    planet = planets[planet_name]

    JST = timezone(timedelta(hours=9))
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    start = datetime(date_obj.year, date_obj.month, date_obj.day, 0, 0, 0, tzinfo=JST)

    altitudes = []
    azimuths = []

    for i in range(25):
        time = start + timedelta(hours=i)
        t = ts.from_datetime(time)
        astrometric = location.at(t).observe(planet)
        alt, az, distance = astrometric.apparent().altaz()
        altitudes.append(alt.degrees)
        azimuths.append(az.degrees)

    return altitudes, azimuths

altitudes, azimuths = calculate_planet_data(
    selected_planet,
    34.3853,
    132.4553,
    now.strftime("%Y-%m-%d")
)

# タブで表示を切り替え
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 高度変化グラフ",
    "🧭 方位変化グラフ",
    "🎯 極座標グラフ",
    "🌐 3D球体グラフ"
])

# タブ1: 高度変化グラフ
with tab1:
    st.subheader("📈 高度変化グラフ（24時間）")
    st.markdown("惑星がいつ地平線より上にあるかを確認できます")

    fig1, ax1 = plt.subplots(figsize=(12, 6))
    hours = list(range(25))

    ax1.plot(hours, altitudes, 'o-', linewidth=2.5, markersize=6,
             label=selected_display_name, color='#2E86AB')
    ax1.axhline(y=0, color='#A23B72', linestyle='--', linewidth=2,
                alpha=0.7, label='地平線')
    ax1.fill_between(hours, 0, altitudes, where=[a > 0 for a in altitudes],
                      alpha=0.3, color='#2E86AB', label='観測可能')

    ax1.set_xlabel('時刻（時）', fontsize=12)
    ax1.set_ylabel('高度（度）', fontsize=12)
    ax1.set_title(f'{selected_display_name}の高度変化 - {now.strftime("%Y年%m月%d日")}',
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    ax1.set_xlim(0, 24)

    st.pyplot(fig1)

    # 統計情報
    max_alt = max(altitudes)
    min_alt = min(altitudes)
    max_time_idx = altitudes.index(max_alt)
    max_time = times[max_time_idx]
    visible_hours = sum(1 for a in altitudes if a > 0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("最高高度", f"{max_alt:.1f}°")
    with col2:
        st.metric("最高高度時刻", max_time.strftime("%H:%M"))
    with col3:
        st.metric("観測可能時間", f"約{visible_hours}時間")
    with col4:
        good_hours = sum(1 for a in altitudes if a > 20)
        st.metric("好観測時間", f"約{good_hours}時間")

# タブ2: 方位変化グラフ
with tab2:
    st.subheader("🧭 方位角変化グラフ（24時間）")
    st.markdown("惑星がどの方角にあるかの変化を確認できます（北:0°/360°、東:90°、南:180°、西:270°）")

    fig2, ax2 = plt.subplots(figsize=(12, 6))

    ax2.plot(hours, azimuths, 'o-', linewidth=2.5, markersize=6,
             label=selected_display_name, color='#F18F01')

    # 方位の参照線
    ax2.axhline(y=0, color='blue', linestyle=':', alpha=0.5, label='北')
    ax2.axhline(y=90, color='green', linestyle=':', alpha=0.5, label='東')
    ax2.axhline(y=180, color='red', linestyle=':', alpha=0.5, label='南')
    ax2.axhline(y=270, color='orange', linestyle=':', alpha=0.5, label='西')

    ax2.set_xlabel('時刻（時）', fontsize=12)
    ax2.set_ylabel('方位角（度）', fontsize=12)
    ax2.set_title(f'{selected_display_name}の方位角変化 - {now.strftime("%Y年%m月%d日")}',
                  fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10, loc='upper right')
    ax2.set_xlim(0, 24)
    ax2.set_ylim(0, 360)

    st.pyplot(fig2)

# タブ3: 極座標グラフ
with tab3:
    st.subheader("🎯 極座標グラフ（方位と高度）")
    st.markdown("惑星の通り道を上から見た図。中心が天頂（真上）、外側が地平線です")

    # データ変換
    az_rad = [np.radians(az) for az in azimuths]
    alt_distance = [90 - alt for alt in altitudes]

    fig3 = plt.figure(figsize=(10, 10))
    ax3 = plt.subplot(111, projection='polar')

    # 惑星の通りをプロット
    ax3.plot(az_rad, alt_distance, marker='o', linestyle='-',
             linewidth=2.5, markersize=6, color='orange')

    # 時刻ラベルを追加（6時間おき）
    for i in range(0, 25, 6):
        ax3.annotate(f'{i}h', xy=(az_rad[i], alt_distance[i]),
                     xytext=(5, 5), textcoords='offset points',
                     fontsize=9, color='red')

    # グラフの設定
    ax3.set_theta_zero_location('N')  # 0度を北に設定
    ax3.set_theta_direction(-1)  # 時計回りに方位を増加
    ax3.set_rlabel_position(135)
    ax3.set_title(f"{selected_display_name}の天球上の軌跡\n{now.strftime('%Y年%m月%d日')}",
                  va='bottom', fontsize=14, fontweight='bold', pad=20)

    # 高度表示のカスタマイズ
    ax3.set_yticks([0, 15, 30, 45, 60, 75, 90])
    ax3.set_yticklabels(['90° (天頂)', '75°', '60°', '45°', '30°', '15°', '0° (地平線)'])

    st.pyplot(fig3)

# タブ4: 3D球体グラフ
with tab4:
    st.subheader("🌐 3D球体グラフ（空のドーム）")
    st.markdown("観測地点から見た天球を3Dで表現。球体の上半分が空、赤い円が地平線です")

    # 3D座標に変換
    x = []
    y = []
    z = []

    for alt, az in zip(altitudes, azimuths):
        alt_rad = np.radians(alt)
        az_rad = np.radians(az)

        z_val = np.sin(alt_rad)
        r = np.cos(alt_rad)
        x_val = r * np.sin(az_rad)
        y_val = r * np.cos(az_rad)

        x.append(x_val)
        y.append(y_val)
        z.append(z_val)

    # 3Dグラフの描画
    fig4 = plt.figure(figsize=(12, 10))
    ax4 = fig4.add_subplot(111, projection='3d')

    # 惑星の軌跡をプロット
    ax4.plot(x, y, z, marker='o', linestyle='-', linewidth=2.5,
             color='orange', markersize=5, label=f'{selected_display_name}の軌跡')

    # 球体のワイヤーフレームを作成
    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi, 30)
    x_sphere = np.outer(np.cos(u), np.sin(v))
    y_sphere = np.outer(np.sin(u), np.sin(v))
    z_sphere = np.outer(np.ones(np.size(u)), np.cos(v))

    # 球体を描画
    ax4.plot_wireframe(x_sphere, y_sphere, z_sphere,
                       color='gray', alpha=0.1, linewidth=0.3)

    # 地平線（赤い円）
    theta = np.linspace(0, 2 * np.pi, 100)
    ax4.plot(np.cos(theta), np.sin(theta), 0,
             color='red', linewidth=2.5, alpha=0.7, label='地平線')

    # 方位の参照線
    ax4.plot([0, 0], [0, 1.2], [0, 0], 'b-', linewidth=2, alpha=0.6)
    ax4.text(0, 1.3, 0, 'N (北)', fontsize=10, color='blue', fontweight='bold')

    ax4.plot([0, 1.2], [0, 0], [0, 0], 'g-', linewidth=2, alpha=0.6)
    ax4.text(1.3, 0, 0, 'E (東)', fontsize=10, color='green', fontweight='bold')

    ax4.plot([0, 0], [0, 0], [0, 1.2], 'r-', linewidth=2, alpha=0.6)
    ax4.text(0, 0, 1.3, 'Zenith\n(天頂)', fontsize=10, color='red', fontweight='bold')

    # 軸の設定
    ax4.set_xlabel('X (東西)', fontsize=11)
    ax4.set_ylabel('Y (南北)', fontsize=11)
    ax4.set_zlabel('Z (高度)', fontsize=11)

    ax4.set_xlim(-1.2, 1.2)
    ax4.set_ylim(-1.2, 1.2)
    ax4.set_zlim(-1.2, 1.2)

    ax4.set_box_aspect([1, 1, 1])

    ax4.set_title(f"3D天球: {selected_display_name}の軌跡\n{now.strftime('%Y年%m月%d日')}",
                  fontsize=13, fontweight='bold', pad=20)

    ax4.legend(loc='upper left', fontsize=10)

    # 視点を調整
    ax4.view_init(elev=20, azim=45)

    st.pyplot(fig4)

    # 説明
    st.info("""
    💡 **3Dグラフの見方**
    - 球体の上半分が「空」を表します
    - 赤い円が地平線（高度0度）
    - オレンジの線が惑星の24時間の軌跡
    - 北(N)・東(E)・天頂(Zenith)の方向を示しています
    """)

# サイドバーに学習メモ
st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 Day 58/100")
st.sidebar.write("**学習内容**:")
st.sidebar.write("- matplotlib基礎")
st.sidebar.write("- 極座標グラフ")
st.sidebar.write("- 3D可視化")
st.sidebar.write("- Streamlitタブ")
st.sidebar.markdown("**#100DaysOfCode** 🚀")
