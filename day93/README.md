# Day 93: ToDoアプリ

100 Days of Code チャレンジ Day 93 — Python + Streamlit で作る Web ベース ToDoアプリ

---

## 概要

タスクの追加・編集・削除・完了管理ができる Web ベース ToDoアプリです。
SQLite でデータを永続化し、期限・優先度による管理や CSV エクスポートに対応しています。
ブラウザ上で動作し、Streamlit のリアクティブ UI でシンプルな操作性を実現します。

---

## 機能要件

### タスク管理
- タスクの追加（タイトル・詳細メモ・期限・優先度）
- タスクの編集・削除
- 完了 / 未完了のトグル
- 優先度設定（高 / 中 / 低）

### 表示・フィルター
- 一覧表示（ツリービュー形式）
- ステータスでフィルター（全件 / 未完了 / 完了済み）
- 優先度・期限でソート
- 期限切れタスクを赤色でハイライト

### データ操作
- CSV エクスポート
- 完了済みタスクの一括削除

---

## 非機能要件

### 使いやすさ
- ブラウザで即時アクセス（localhost）
- フィルター・ソートをサイドバーに集約し、操作をシンプルに
- 日本語 UI

### 信頼性
- SQLite によるデータ永続化（アプリ終了後もデータを保持）
- 削除・一括削除時の確認ダイアログ

### 保守性
- DB 操作・UI ロジック・データモデルの分離
- 各ファイルが単一責任を持つシンプルな構成
- `st.session_state` で状態管理を一元化

---

## 技術スタック

| 要素 | 技術 |
|------|------|
| 言語 | Python 3.10+ |
| UI フレームワーク | Streamlit |
| データベース | SQLite3（標準ライブラリ） |
| その他 | pandas（CSV エクスポート）、datetime（期限管理） |

---

## ファイル構成

```
day93/
├── app.py           # Streamlit メインアプリ（UI + Controller）
├── db.py            # DB操作（CRUD）— Model 層
├── task.py          # Task データクラス（@dataclass）
├── exporter.py      # CSV エクスポート処理
├── todo.db          # SQLite データベース（自動生成）
└── README.md
```

### 各ファイルの責務

| ファイル | 責務 |
|----------|------|
| `app.py` | Streamlit UI、サイドバー、フォーム、一覧表示 |
| `db.py` | SQLite への CRUD 操作、DB 初期化 |
| `task.py` | `Task` データクラス定義（id, title, memo, due_date, priority, done） |
| `exporter.py` | タスク一覧の pandas DataFrame → CSV 変換 |

---

## 実行方法

```bash
pip install streamlit pandas
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

### 必要環境
- Python 3.10 以上
- streamlit
- pandas

---

## スクリーンショット

*（実装後に追加予定）*

---

## Azure Container Apps デプロイ手順

> このアプリを Azure Container Apps にデプロイした記録です。
> SQLite はコンテナ再起動でデータが消えるため、実用には向きませんが、デプロイ手順の学習として実施しました。

---

### 前提条件

- Docker Desktop インストール済み
- Azure アカウント作成済み

---

### Step 1: Azure CLI インストール

```bash
# 公式インストーラーを https://learn.microsoft.com/ja-jp/cli/azure/install-azure-cli-windows からダウンロードして実行

# インストール確認（バージョンが表示されればOK）
az version

# Azureアカウントにログイン（ブラウザが開いて認証する）
az login
```

---

### Step 2: Azureリソース作成

```bash
# リソースグループ作成（関連リソースをまとめる箱）
az group create --name rg-todo-app --location japaneast

# Azure Container Registry (ACR) 作成（Dockerイメージの保存先）
az acr create \
  --resource-group rg-todo-app \
  --name <ACR名> \
  --sku Basic

# Container Apps Environment 作成（Container Appsを動かす実行環境）
az containerapp env create \
  --name todo-env \
  --resource-group rg-todo-app \
  --location japaneast
```

---

### Step 3: Dockerイメージのビルド & ACRにプッシュ

```bash
# ACRにログイン（ローカルのDockerをACRに接続する）
az acr login --name <ACR名>

# Dockerイメージをビルド（Dockerfileをもとにイメージを作成）
docker build -t <ACR名>.azurecr.io/todo-app:latest .

# ビルドしたイメージをACRにアップロード
docker push <ACR名>.azurecr.io/todo-app:latest
```

---

### Step 4: Container Apps にデプロイ

```bash
# Container Apps を作成してデプロイ（完了後にアプリのURLが表示される）
az containerapp create \
  --name todo-app \
  --resource-group rg-todo-app \
  --environment todo-env \
  --image <ACR名>.azurecr.io/todo-app:latest \
  --registry-server <ACR名>.azurecr.io \
  --target-port 8501 \
  --ingress external \
  --query properties.configuration.ingress.fqdn
```

> `--target-port 8501` は Streamlit のデフォルトポートに合わせている。
> `--ingress external` で外部からアクセス可能にする。

---

### Step 5: 動作確認

```bash
# Step 4 で表示された FQDN をブラウザで開く
# https://<表示されたFQDN>
```

---

### Step 6: リソース削除

```bash
# リソースグループごと全削除（ACR・Container Apps・Environmentがまとめて消える）
az group delete --name rg-todo-app --yes
```

> ACR は Basic プランで約500円/月かかるため、学習後は忘れずに削除する。

---

### 振り返り

| 項目 | 評価 |
|------|------|
| デプロイ自体の難易度 | 低い（CLIコマンドを順番に実行するだけ） |
| SQLite との相性 | 悪い（コンテナ再起動でデータが消える） |
| Streamlit との相性 | やや注意（WebSocketの挙動に注意が必要） |
| コスト | ACRが常時課金されるため学習後は削除推奨 |

実用化する場合は DB を PostgreSQL（Azure Database for PostgreSQL）に移行するか、App Service への変更を検討する。

---

### 手順を通して学んだこと

#### Azure の構造が見えてきた

「アプリを Azure に上げる」と一言でいっても、実際には役割の異なる部品を順番に組み合わせる作業だと分かりました。

```
箱を作る → イメージ置き場を作る → 実行環境を作る → その上にアプリを置く
```

今回の手順を分解すると、次のようになります。

```
ローカルで Docker イメージを作る
        ↓
ACR にイメージを保存する
        ↓
Container Apps が ACR からイメージを取得して動く
        ↓
リソースグループがそれら全体をまとめて管理する
```

つまり Azure は「1つのサービス」ではなく、役割の異なるサービスを組み合わせて動かす仕組みでした。

> Azure にデプロイするとは、アプリを一度に置くことではなく、
> 置き場所・実行環境・管理単位を組み合わせて動かすことだった。

---

### Azure サービス用語解説

| サービス | 役割 |
|----------|------|
| **リソースグループ** | 関連するリソースをまとめて管理する単位。削除もグループ単位で一括実行できる |
| **ACR（Azure Container Registry）** | Docker イメージを保存・管理するプライベートレジストリ。Azure 上の Docker Hub のような役割 |
| **Container Apps Environment** | Container Apps を動かすための共有実行基盤。ネットワークやログなどの共通設定をまとめて持つ |
| **Container App** | 実際に動作するアプリ本体。Environment 上で動き、外部公開の設定も行える |
