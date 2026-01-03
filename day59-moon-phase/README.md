# 🌙 月齢と太陽・月の軌道シミュレーター

広島から見た太陽と月の動きを3Dで可視化するStreamlitアプリケーション

## 📝 概要

Skyfield を用いて月齢（朔望月）と太陽・月の見かけの動きを計算し、
高度・方位・極座標・3D天球として可視化するシミュレーターを作成した。
最終的に Streamlit アプリとして動作する形まで実装。

## ✨ 機能

- **日付選択**: 任意の日付の天体の動きを計算
- **3D天球ドーム**: 広島の空を3D球体で可視化
- **黄道面俯瞰図**: 宇宙から見た地球・太陽・月の配置
- **24時間アニメーション**: 1日の太陽と月の軌道を動的表示
- **月齢計算**: 黄経差に基づく正確な月齢情報
- **軌道の軌跡**: 地平線の上下を含む全軌道表示

## 使い方

### 必要な環境

- Python 3.8以上
- pip

### インストール

### パッケージのインストール
```bash
pip install -r requirements.txt
```

### 実行

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

## 使用方法

1. サイドバーで日付を選択
2. アニメーションが自動的に再生され、24時間の太陽と月の動きを表示
3. 左側: 宇宙から見た配置（黄道面俯瞰）
4. 右側: 広島から見た空（3D天球ドーム）
5. サイドバーで現在の月齢情報を確認

## 観測地点

- **都市**: 広島市
- **緯度**: 34.3853°
- **経度**: 132.4553°

## 月齢について

月齢は太陽と月の黄経差から計算されます：

| 状態 | 黄経差 | 月齢 |
|------|--------|------|
| 新月（朔） | 0° | 0.0日 |
| 上弦 | 90° | 約7.4日 |
| 満月（望） | 180° | 約14.8日 |
| 下弦 | 270° | 約22.1日 |

## 技術的詳細

### 座標変換

高度・方位角から3D直交座標への変換：

```python
def get_xyz(alt_deg, az_deg):
    alt_r = np.radians(alt_deg)
    az_r = np.radians(az_deg)
    x = np.cos(alt_r) * np.sin(az_r)
    y = np.cos(alt_r) * np.cos(az_r)
    z = np.sin(alt_r)
    return x, y, z
```

### 天体暦データ

- JPL DE421天体暦ファイル（`de421.bsp`）を使用
- 初回実行時に自動ダウンロード

### アニメーション

- matplotlib FuncAnimationを使用
- blitモードで効率的な描画
- HTML5形式でStreamlitに埋め込み

## 学習内容
### Day 59で学んだこと

- 天体計算ライブラリ（Skyfield）の使用
- 月齢を角度で求める
- 3D座標系での可視化
- matplotlibでのアニメーション作成
- 球面座標と直交座標の変換  
詳細な学習ノートは [notes.md](notes.md) を参照してください。

## ライセンス

MIT License

##  参考資料

- [Skyfield](https://rhodesmill.org/skyfield/) - 天体位置計算
- [JPL](https://www.jpl.nasa.gov/) - 天体暦データ（DE421）
- [Streamlit](https://streamlit.io/) - Webアプリフレームワーク
- [@ciscorn (Taku Fukada) 人工衛星の軌道をPythonでアニメーションにしてみよう]  
- https://qiita.com/ciscorn/items/80b3a3f526316f78b24a - Qiita

## Author
作成者: Miki Makino
日付: 2026年1月3日