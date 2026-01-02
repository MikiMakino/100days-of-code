# Day 58: 惑星の位置可視化アプリ 📊

100 Days of Astronomy Apps - Day 58

## 概要
選択した惑星の24時間の動きを4つの視点でリアルタイムに可視化するStreamlitアプリです。
2Dと3Dの両面から惑星の動きをとらえて、直感的に理解できるようにしました。

## 🌟 機能

### 4つの可視化タブ
1. **📈 高度変化グラフ** - 惑星がいつ地平線より上にあるかを時系列で表示
2. **🧭 方位変化グラフ** - 惑星がどの方角に見えるかの変化を表示
3. **🎯 極座標グラフ** - 天球上の惑星の軌跡を上から見た図
4. **🌐 3D球体グラフ** - 観測地点から見た天球を3次元で表現

### その他の機能
- 🪐 5つの惑星から選択（水星、金星、火星、木星、土星）
- 📍 観測地点: 広島市（カスタマイズ可能）
- 📅 日本時間（JST）で表示
- 📈 詳細統計情報
  - 最高高度
  - 最高高度時刻
  - 観測可能時間
  - 好観測時間（高度20度以上）

## インストール

### 必要な環境
- Python 3.10以上
- pip

### パッケージのインストール
```bash
pip install -r requirements.txt
```

## 実行方法

### Streamlitアプリを実行
```bash
# 仮想環境を有効化（初回のみ）
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# パッケージをインストール（初回のみ）
pip install -r requirements.txt

# アプリを起動
streamlit run app.py
```

ブラウザで http://localhost:8501 が自動的に開きます。

### 学習用スクリプトを実行

**Skyfieldの基本を学ぶ:**
```bash
python learn_skyfield.py
```
- Skyfieldのトップページにあるプログラムをターミナルで確認
  Skyfield: https://rhodesmill.org/skyfield/
  参考記事:note 天文と気象（とその他いろいろ）「Skyfieldを使いながら、天球座標系を学ぶ」
  https://note.com/symmetrybreaking/n/n74dbbf578fb0


**Jupyter Notebookで学習:**
```bash
jupyter notebook learn_skyfield.ipynb
```
- インタラクティブに学習
- 2Dグラフ、極座標、3Dグラフを実践

## 使い方

1. サイドバーから惑星を選択
2. 4つのタブを切り替えて様々な視点で可視化
3. 統計情報で観測計画を立てる

## 各グラフの見方

### 📈 高度変化グラフ
- 横軸: 時刻（0時〜24時）
- 縦軸: 高度（度）
- 青い領域: 観測可能な時間帯（高度0度以上）
- 赤い点線: 地平線

### 🧭 方位変化グラフ
- 横軸: 時刻（0時〜24時）
- 縦軸: 方位角（度）
  - 0°/360°: 北
  - 90°: 東
  - 180°: 南
  - 270°: 西

### 🎯 極座標グラフ
- 中心: 天頂（真上）
- 外側: 地平線
- 角度: 方位（北が上）
- オレンジの線: 惑星の軌跡
- 赤いラベル: 時刻（6時間おき）

### 🌐 3D球体グラフ
- 球体の上半分: 空
- 赤い円: 地平線
- オレンジの線: 惑星の24時間の軌跡
- 青線(N): 北の方向
- 緑線(E): 東の方向
- 赤線(Zenith): 天頂

## 学習内容

### Day 58で学んだこと
- **Skyfield**: 天体位置計算ライブラリの使い方
- **Matplotlib**: 2Dグラフ、極座標グラフ、3Dグラフの作成
- **Streamlit**: タブ機能、レイアウト、キャッシング
- **天文学の基礎**:
  - 高度と方位角
  - 地平座標系
  - 球面座標から直交座標への変換
  - 日本時間とUTCの扱い

詳細は [notes.md](notes.md) を参照してください。

## 技術スタック
- **Python 3.13**
- **Streamlit** - Webアプリフレームワーク
- **Skyfield** - 天体位置計算
- **Matplotlib** - データ可視化
- **NumPy** - 数値計算

## ファイル構成
```
day58_planet_position/
├── app.py                    # メインアプリ
├── learn_skyfield.py         # Skyfield学習スクリプト
├── learn_skyfield.ipynb      # Jupyter Notebook（詳細学習用）
├── requirements.txt          # 依存パッケージ
├── README.md                 # このファイル
├── notes.md                  # 学習記録
└── .gitignore               # Git除外設定
```

## 今後の改善案

## トラブルシューティング

### 文字化けが発生する場合
日本語フォントが必要です。以下を試してください：
```python
# Windowsの場合
matplotlib.rcParams['font.sans-serif'] = ['MS Gothic']

# Mac/Linuxの場合
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans']
```

### 初回実行が遅い
天体暦データ（de421.bsp、約17MB）のダウンロードに時間がかかります。2回目以降は高速です。

## 参考資料
- [Skyfield公式ドキュメント](https://rhodesmill.org/skyfield/)
- [Matplotlib公式ドキュメント](https://matplotlib.org/)
- [Streamlit公式ドキュメント](https://docs.streamlit.io/)

## ライセンス
MIT

---

**#100DaysOfCode #Day58 #Python #Streamlit #Skyfield #Astronomy #DataVisualization** 🌌

## Author
作成者: Miki Makino
日付: 2026年1月2日
