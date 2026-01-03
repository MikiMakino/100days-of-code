# Day 59/100 - 月齢と太陽・月の軌道シミュレーター

## 📚 学習内容

### 1. Skyfieldライブラリによる天体計算

#### 月齢の計算
```python
from skyfield import almanac
from skyfield.api import load

eph = load('de421.bsp')  # 天体暦データ
ts = load.timescale()
t = ts.now()

moon_phase = almanac.moon_phase(eph, t)
moon_age = (moon_phase.degrees / 360) * 29.53
```

- `de421.bsp`: JPL (NASA) の天体暦データファイル
- 月齢は太陽と月の黄経差から計算
- 29.53日で1周期（朔望月）

#### 観測地点の設定
```python
from skyfield.api import wgs84

hiroshima = wgs84.latlon(34.3853, 132.4553)
observer = eph['earth'] + hiroshima
```

- WGS84座標系で緯度経度を指定
- 観測者 = 地球 + 地表の位置

### 2. 太陽・月の高度と方位の計算

```python
t_list = ts.utc(2026, 1, 3, range(24))  # 24時間分
sun = eph['sun']
sun_positions = observer.at(t_list).observe(sun).apparent().altaz()

altitudes = sun_positions[0].degrees   # 高度
azimuths = sun_positions[1].degrees    # 方位角
```

- **高度 (altitude)**: 地平線からの角度 (-90° ~ 90°)
- **方位角 (azimuth)**: 北を0°として時計回りの角度

### 3. matplotlibアニメーション

#### FuncAnimationの基本構造
```python
from matplotlib.animation import FuncAnimation

fig, ax = plt.subplots()
point, = ax.plot([], [], 'ro')

def update(frame):
    point.set_data([frame], [altitudes[frame]])
    return point,

ani = FuncAnimation(fig, update, frames=24, interval=200, blit=True)
```

- `frames`: アニメーションのコマ数
- `interval`: 各コマの間隔（ミリ秒）
- `blit=True`: 効率的な描画（変更部分のみ更新）

### 4. 極座標プロット（天球図）

```python
ax = fig.add_subplot(111, polar=True)
ax.set_theta_zero_location('N')  # 北を上に
ax.set_theta_direction(-1)       # 時計回り
ax.set_ylim(0, 90)               # 中心から地平線まで

# 高度→半径の変換
r = 90 - current_alt
```

- 極座標で天球を表現
- 中心 = 天頂（真上）、外周 = 地平線

### 5. 3D天球ドームの描画

#### 座標変換（高度・方位 → 3D直交座標）
```python
def get_xyz(alt_deg, az_deg):
    alt_r = np.radians(alt_deg)
    az_r = np.radians(az_deg)

    x = np.cos(alt_r) * np.sin(az_r)
    y = np.cos(alt_r) * np.cos(az_r)
    z = np.sin(alt_r)
    return x, y, z
```

#### 球体の網目を作成
```python
u, v = np.mgrid[0:2*np.pi:30j, 0:np.pi:30j]  # 全球体
x_sphere = np.cos(u) * np.sin(v)
y_sphere = np.sin(u) * np.sin(v)
z_sphere = np.cos(v)
ax.plot_wireframe(x_sphere, y_sphere, z_sphere)
```

### 6. Streamlitアプリケーション化

#### レイアウト設定
```python
st.set_page_config(page_title="Sky Dome Simulator", layout="wide")
col1, col2 = st.columns([1, 3])  # 左右の幅比率
```

#### アニメーションの埋め込み
```python
import streamlit.components.v1 as components

ani = FuncAnimation(fig, update, frames=24, interval=150, blit=True)
components.html(ani.to_jshtml(), height=600)
```

### 7. 月齢情報の計算（より正確な方法）

```python
_, s_lon, _ = s_noon.ecliptic_latlon()  # 太陽の黄経
_, m_lon, _ = m_noon.ecliptic_latlon()  # 月の黄経

# 月が太陽からどれだけ進んでいるか (0〜360度)
phase_angle = (m_lon.degrees - s_lon.degrees) % 360
moon_age = (phase_angle / 360 * 29.53)
```

## 🛠️ 使用ライブラリ

- **skyfield**: 天体位置計算
- **matplotlib**: グラフ描画・アニメーション
- **streamlit**: Webアプリケーション化
- **numpy**: 数値計算
- **pandas**: データフレーム（表の表示）

## 📊 実装した機能

1. 日付選択による天体位置計算
2. 広島から見た太陽・月の24時間アニメーション
3. 3D天球ドームの可視化
4. 地平線より下も含む全球体表示
5. 軌道の軌跡表示
6. 月齢情報の表示（黄経差による計算）
7. 月齢の目安表（新月・上弦・満月・下弦）

## 💡 学んだポイント

### 天文学的知識
- 黄道座標系と地平座標系の違い
- 月齢と太陽・月の黄経差の関係
- 観測地点による見え方の違い

### プログラミング技術
- 3D座標系での描画とカメラアングル設定
- アニメーションの効率的な更新（blit）
- Streamlitでの複数アニメーション表示
- データキャッシング（`@st.cache_resource`）

### 数学的変換
- 球面座標 → 直交座標の変換
- 極座標での可視化
- 角度の正規化（0-360度）

## 🎯 次のステップ

- [ ] 任意の緯度経度での観測に対応
- [ ] 星座や惑星の追加
- [ ] 日の出・日の入り時刻の計算
- [ ] 月の満ち欠けの視覚的表現
- [ ] インタラクティブな視点変更機能
