# Day 91: JCL ジェネレーター

メインフレームからデータをダウンロードするための SORT ジョブ JCL を GUI で生成する Python ツール。

## 概要

データセットのレイアウト定義（YAML）をもとに、INCLUDE/OMIT 条件や出力形式を GUI で設定するだけで、メインフレーム用の JCL を自動生成します。

## 機能要件

| # | 機能 | 説明 |
|---|------|------|
| F1 | JOBカード生成 | ユーザーコード入力で固定フォーマットの JOB カードを生成 |
| F2 | レイアウト定義読み込み | YAML ファイルからフィールド定義を読み込み、ドロップダウンで選択 |
| F3 | DSN 入力 | 入力 DSN・出力 DSN をテキスト入力 |
| F4 | INCLUDE 条件設定 | フィールド選択・演算子選択・値入力で抽出条件を設定 |
| F5 | 複数条件対応 | 条件を複数追加し、AND/OR で組み合わせ |
| F6 | 型自動変換 | CH → `C'値'`、PD → `P'値'` を自動変換 |
| F7 | 出力形式選択 | 全項目 COPY（`SORT FIELDS=COPY`）または項目絞り（`OUTREC FIELDS`）を選択 |
| F8 | JCL プレビュー | 生成前に GUI 上で JCL 内容を確認 |
| F9 | JCL 自動保存 | `output/` フォルダに `出力DSN名_YYYYMMDD_HHMMSS.jcl` で自動保存 |

## 非機能要件

| # | 項目 | 内容 |
|---|------|------|
| N1 | 動作環境 | Windows（メインフレーム接続 PC 上で動作） |
| N2 | 拡張性 | YAML ファイルを追加するだけで新しいデータセットに対応可能 |
| N3 | 保守性 | JCL 生成ロジックと GUI を分離し、独立して修正可能 |
| N4 | 安全性 | JCL 生成のみ（メインフレームへの直接接続・実行は行わない） |
| N5 | 入力検証 | 必須項目未入力・不正値はエラーメッセージで通知 |
| N6 | 文字コード | 生成 JCL は ASCII 保存（メインフレーム転送時に変換） |

## 技術スタック

| 項目 | 採用技術 | 理由 |
|------|---------|------|
| 言語 | Python 3.10+ | 標準ライブラリが豊富、保守しやすい |
| GUI | tkinter | Python 標準、追加インストール不要 |
| 設定ファイル | YAML | 可読性が高く、コメントが書ける |
| YAML パース | PyYAML | Python 定番ライブラリ |
| 外部ライブラリ | PyYAML のみ | 依存を最小限に |

## ディレクトリ・ファイル構成

```
day91-JCL/
├── main.py              # エントリーポイント・アプリ起動
├── gui.py               # tkinter GUI（画面構築・イベント処理）
├── jcl_generator.py     # JCL 生成ロジック（JOBカード・SORT文組み立て）
├── layout_loader.py     # YAML レイアウト定義の読み込み・管理
├── config.py            # 固定値定義（JOBカードパラメータ・保存フォルダ）
├── layouts/             # データセットレイアウト定義（YAML）
│   └── example.yaml     # サンプルレイアウト
├── output/              # 生成 JCL 保存フォルダ（自動作成）
├── requirements.txt     # 依存ライブラリ
└── README.md
```

### 各ファイルの役割

| ファイル | 役割 |
|---------|------|
| `main.py` | アプリの起動・初期化 |
| `gui.py` | 画面レイアウト・ボタンイベント・入力値の受け渡し |
| `jcl_generator.py` | JOBカード・SORTIN・SORTOUT・SYSIN の文字列生成 |
| `layout_loader.py` | `layouts/` フォルダの YAML 一覧取得・フィールド定義読み込み |
| `config.py` | CLASS・MSGCLASS 等の固定パラメータ・出力フォルダパス |
| `layouts/*.yaml` | データセットごとのフィールド定義（名前・開始位置・長さ・型） |
| `output/` | 生成された JCL ファイルの保存先 |

## インストール

```bash
pip install pyyaml
```

※ tkinter は Python 標準ライブラリに含まれています。

## レイアウト定義ファイル（YAML）

`layouts/` フォルダに YAML ファイルを作成することで、データセットのフィールド定義を登録できます。

```yaml
# layouts/buhin_seishin.yaml
dataset_name: BUHIN.SEISHIN
description: 部品番号世代ファイル
lrecl: 200

fields:
  - name: 部品番号
    start: 1
    length: 15
    type: CH

  - name: 世代
    start: 16
    length: 3
    type: CH

  - name: 単価
    start: 19
    length: 5
    type: PD    # パック十進数：5バイト = 最大9桁
```

### フィールド型

| type | 説明 | JCL での値形式 |
|------|------|---------------|
| CH | 文字（Character） | `C'値'` |
| PD | パック十進数（Packed Decimal） | `P'値'` |

## 使い方

```bash
python main.py
```

### 操作手順

1. **基本設定**
   - ユーザーコードを入力
   - レイアウト定義をドロップダウンから選択
   - 入力 DSN・出力 DSN を入力

2. **抽出条件設定**
   - フィールドをドロップダウンから選択
   - 演算子（EQ / NE / GT / LT / GE / LE）を選択
   - 値を入力（型に応じて自動変換）
   - 条件が複数の場合は AND / OR を指定
   - 「条件追加」ボタンで条件を増やす

3. **出力設定**
   - 「全項目 COPY」または「項目を絞る」を選択
   - 項目を絞る場合は出力するフィールドにチェック

4. **JCL 生成**
   - 「JCL 生成」ボタンをクリック
   - `output/` フォルダに JCL ファイルが保存される
   - プレビューで内容を確認可能

## 生成される JCL の例

```jcl
//USRXXXXX JOB (ACCT),'JCL GENERATOR',
//             CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID
//*
//STEP1    EXEC PGM=SORT
//SYSOUT   DD SYSOUT=*
//SORTIN   DD DSN=BUHIN.SEISHIN,DISP=SHR
//SORTOUT  DD DSN=OUTPUT.DATASET,DISP=(NEW,CATLG,DELETE),
//             SPACE=(CYL,(10,5),RLSE),
//             DCB=(RECFM=FB,LRECL=200,BLKSIZE=0)
//SYSIN    DD *
  SORT FIELDS=COPY
  INCLUDE COND=(1,15,CH,EQ,C'ABC001         ')
/*
```

### 出力ファイル名

```
output/OUTPUT.DATASET_20260311_143000.jcl
```

## 画面構成

```
┌─────────────────────────────────────────┐
│  [1] 基本設定                            │
│  ユーザーコード: [____]                   │
│  レイアウト定義: [ドロップダウン ▼]        │
│  入力 DSN:      [____________________]   │
│  出力 DSN:      [____________________]   │
├─────────────────────────────────────────┤
│  [2] 抽出条件                            │
│  ┌──────┬────┬────┬──────┬──────────┐   │
│  │フィールド│型│演算子│値   │AND/OR    │   │
│  ├──────┼────┼────┼──────┼──────────┤   │
│  │部品番号│CH│ EQ │ABC01│          │   │
│  │世代   │CH│ EQ │001  │AND       │   │
│  └──────┴────┴────┴──────┴──────────┘   │
│  [条件追加] [条件削除]                    │
├─────────────────────────────────────────┤
│  [3] 出力設定                            │
│  ○ 全項目 COPY  ○ 項目を絞る             │
│  （絞る場合：フィールド選択チェックボックス）│
├─────────────────────────────────────────┤
│        [JCL 生成]  [プレビュー]           │
└─────────────────────────────────────────┘
```
