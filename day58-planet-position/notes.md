# Day 58: 惑星の位置可視化アプリ

## 日付
2026年1月2日

## 今日のテーマ
Skyfieldを使って惑星の正確な位置（高度・方位）を算出する
数値データを2Dと3Dで可視化する

## 今日学んだこと

### 1. Skyfieldでの天体計算

#### 基本的な使い方
##### 天体暦データを読み込む。  
de421.bsp：NASA JPL が計算した惑星の位置データ（1900〜2050年）
```python
planets = load('de421.bsp')
earth = planets['earth']
ts = load.timescale()
```
##### 観測地点を設定（広島）
- earth + wgs84.latlonは単なる緯度経度ではなく**地球の楕円体モデル(WGS84)上の正確な地点を表す。
- WGS84: 「世界測地系1984」の略でGPSでも使われている世界標準の測地系
- earth + は太陽系の中心から見た地球上の広島に立っている自分を宇宙的なベクトルとして定義している。  
> 少し歪んだ地球の表面に立っている自分！

```python
location = earth + wgs84.latlon(34.3853, 132.4553)
```

##### 惑星を観測する
- observe()：観測者から見た天体の位置を計算
- apparent()：光の到達時間や視位置（見かけの位置）を考慮
- altaz()：地平座標系（高度・方位角）で返す

```python
planet = planets['mars']
astrometric = location.at(t).observe(planet)
alt, az, distance = astrometric.apparent().altaz()
```

### 2. 地平座標系（Alt-Az）
- **高度（Altitude）**: 地平線を0°、天頂を+90°、地面下を-90°とする角度
- **方位角（Azimuth）**: 北を0°として、東回りに360°まで測る角度  
※ Skyfield の alt / az は Angle オブジェクト  
使用時は .degrees を参照

### 3. 球面座標 → 直交座標への変換（3D可視化）
Skyfieldが返す「角度」を  
3D空間の座標に変えるロジック  
  
**考え方**  
- ラジアンの役割：0から360の角度を数学が理解できる言語（ラジアン）に変換。
- 天球モデル: 観測者を中心にした仮想的な球を考えて、その表面に天体を配置するモデル。
    - Z軸：高度（天頂方向）
    - r（水平半径）：天体が地平線からどれだけ離れているかを表す「横方向の広がり」。
    - X,Y軸：方位角（東西・南北）

```python
# 高度と方位角から3D座標を計算
alt_rad = np.radians(alt)
az_rad = np.radians(az)

# 高さ（Z軸）
z = np.sin(alt_rad)

# 水平面での半径
r = np.cos(alt_rad)

# X軸（東西）、Y軸（南北）
x = r * np.sin(az_rad)
y = r * np.cos(az_rad)
```
- 高度が高いほど（天頂に近い）cos(alt)が小さくなり、rは小さくなる。　
  天体は天球の中心付近に描かれる。

- 高度が低いほど（地平線に近い）cos(alt)が大きくなり、rは大きくなる。
  天体は天球の縁（地平線付近）に描かれる。


### 4. 時刻の扱い
#### 日本時間とUTC
```python
JST = timezone(timedelta(hours=9))
now_jst = datetime.now(JST)
t = ts.from_datetime(now_jst)
```
- Skyfieldの計算基準はUTC
- タイムゾーン未指定の datetime を渡すと9時間ずれる

### 5. Matplotlibによる表現
#### 極座標（Polar）
- 北を0°
- 時計回りに設定
- 実際のコンパスと一致する空の見え方

#### 3Dワイヤーフレーム
- np.outer で球体を生成
- Skyfieldの軌道(惑星位置)を天球上に重ねて描画

### 6. Streamlitの実装とキャッシング

```python
@st.cache_resource  
def load_ephemeris():
    return load('de421.bsp')

@st.cache_data     
def calculate_planet_data(planet_name, lat, lon, date_str):
    return altitudes, azimuths
```

- @st.cache_resource : 変わらないリソース
- @st.cache_data     : 条件で変わる計算結果（惑星や日付で変わる）
- キャッシュとは、一度計算したり読み込んだりしたデータを、すぐに取り出せる場所に一時保管する仕組みのこと。
  
  
**計算負荷軽減**  
24時間分の天体計算は重くなる。

**リソースの管理**  
SpiceKernel(de421.bsp 天体暦ファイル)はNASAが計算した1900年から2050年までの全惑星の未来予想図で変わらない。  
17MBほどもある巨大なデータファイルなので最初に1回だけ読み込む。  
メモリ（RAM）の中に置いておくので2回目からは一瞬でアクセス可能になる。　　


## 戸惑った点と解決方法

### 1. JSTとUTCの混同
**問題**: グラフの時刻が9時間ずれる。  
**解決**: `timezone`を明示する。  
**Point**: Skyfieldが求めている（計算につかう）のはUTCなので、最後の1行でUTCに戻す必要がある。 

```python
JST = timezone(timedelta(hours=9)) # JSTはUTCから見てプラス9時間のタイムゾーンという定義
now = datetime.now(JST)            # 現在時刻をユーザーが見るJSTとして取得
t = ts.from_datetime(now)          # Skyfieldがラベルを見て、JSTをUTCに自動変換して計算
```

### 2. 「地図」と「空」では右と左が逆

- X軸のプラス: 東
- Y軸のプラス: 北
- z軸のプラス: 天頂
天文学の方位（北0°・東回り）に合わせるため  
通常とは逆に sin / cos を使う。  
数学では X = cos(横軸), Y = sin（縦軸） が基本。

```python
x = r * np.sin(az_rad)  
y = r * np.cos(az_rad)  
```


## 🔗 参考資料

### 公式ドキュメント
- [Skyfield - Topocentric Positions](https://rhodesmill.org/skyfield/positions.html)
- [Matplotlib - Polar Plots](https://matplotlib.org/stable/gallery/pie_and_polar_charts/polar_demo.html)
- [Matplotlib - 3D Plotting](https://matplotlib.org/stable/gallery/mplot3d/index.html)
- [Streamlit - Tabs](https://docs.streamlit.io/library/api-reference/layout/st.tabs)

### 参考にした記事
- 天文と気象（とその他いろいろ）著  
  「Skyfieldを使いながら、天球座標系を学ぶ」  
   https://note.com/symmetrybreaking/n/n74dbbf578fb0

## 💭 感想
4つの異なる視点で惑星の動きを可視化できたことで、天体の動きがより直感的に理解できるようになった。
星のソムリエ®講座で学習中の単位や単語などの復習ができた。
Jupyter Notebookで段階的に学習し、最終的にStreamlitアプリに統合するという学習フローが効果的だった。

## 🎯 Day 58の成果
- ✅ 天球モデルでの可視化ができた
- ✅ 数学座標系と天文学的方位（北0°・東回り）の違いを意識した可視化ができた
- ✅ 高度（alt）を高さ（z）、方位角（az）を 水平展開（x, y）として解釈できた
- ✅ 球面座標から直交座標への変換をなんとか理解した
- ✅ 上記の理解を、2D・極座標・3Dの複数表現をStreamlitアプリに実装した

---

**#100DaysOfCode #Day58 #Python #Streamlit #Skyfield #Astronomy #DataVisualization** 🌌
