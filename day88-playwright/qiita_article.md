---
title: Playwrightでconnpassの参加者CSVダウンロードを自動化する
tags: Python Playwright connpass 自動化 スクレイピング
---

## はじめに

WiDS HIROSHIMAのワークショップで **Playwright** を教えてもらいました。Pythonからブラウザ操作を自動化できるライブラリです。

これまでWEBアプリからのダウンロード自動化には **Power Automate Desktop** を使っていたのですが、Playwrightならコードで完結するので管理しやすそうだと感じ、実際に試してみることにしました。

題材として選んだのは、connpassで自分が管理者になっているイベントの**申込者リストCSVダウンロード**の自動化です。毎回ブラウザを開いてログインして、管理画面に行って、CSVボタンを押して……という手順を、スクリプト一発で済むようにしました。

## 作ったもの

connpassのイベントURLを渡すと、以下を自動で行うPythonスクリプトです。

1. イベントページを開く
2. ログイン状態を確認（未ログインなら手動ログインを待機）
3. 「申込者を管理する」→「CSVダウンロード」を自動クリック
4. CSVファイルをローカルに保存

## 環境

- Python 3.11+
- Playwright (`pip install playwright && playwright install`)

## ディレクトリ構成

```
day89/
├── app.py          # メインスクリプト
├── config.toml     # 設定ファイル
└── test.py         # 動作確認用
```

## 設定ファイル（config.toml）

TOMLで設定を外出しにしています。保存先やタイムアウト値、よく使うイベントURLをまとめて管理できます。

```toml
[paths]
base_dir = "~/Downloads/connpass_csv"
error_dir = "_errors"

[browser]
headless = false

[timeout]
page_load_ms = 60_000
login_wait_ms = 300_000   # 手動ログイン待機（5分）
login_check_ms = 2_000
download_ms = 60_000

[events]
urls = ["https://plug.connpass.com/event/381240/"]
```

`headless = false` にしているのがポイントです。connpassはOAuth連携でのログインが必要なため、初回は手動でログインする必要があります。

## コードのポイント

### 1. ログイン判定

connpassにログイン済みかどうかは「申込者を管理する」リンクの有無で判定しています。

```python
def ensure_logged_in_and_get_manage_link(page, event_url, timeout_ms=None):
    page.goto(event_url, wait_until="domcontentloaded",
              timeout=TIMEOUT["page_load_ms"])

    manage_link = page.get_by_role("link", name="申込者を管理する").first

    try:
        # まず短時間（2秒）で判定
        manage_link.wait_for(state="visible", timeout=TIMEOUT["login_check_ms"])
        return manage_link
    except PWTimeoutError:
        pass

    # 見つからなければ手動ログインを促す
    print("ログイン画面を検知しました。ブラウザで手動ログインしてください…")
    manage_link.wait_for(state="visible", timeout=timeout_ms)
    return manage_link
```

**2段階の待機**がミソです。

- まず **2秒** だけ待つ → ログイン済みならすぐ見つかる
- タイムアウトしたら **最大5分** 手動ログインを待つ

これにより、ログイン済みのときはサクッと進み、未ログインのときは人間が操作する余裕を確保しています。

### 2. ログイン画面の検知

ログイン画面かどうかを複数のパターンでゆるく検知します。

```python
def is_login_page(page):
    candidates = [
        page.get_by_role("button", name=re.compile(r"ログイン|Login", re.I)),
        page.get_by_role("link", name=re.compile(r"ログイン|Login", re.I)),
        page.locator("form:has-text('ログイン')"),
        page.locator("input[type='password']"),
    ]
    for loc in candidates:
        try:
            if loc.first.is_visible():
                return True
        except Exception:
            continue
    return False
```

connpassのUI変更に耐えられるよう、ボタン・リンク・フォーム・パスワード入力欄のいずれかが見つかれば「ログイン画面」と判定しています。

### 3. CSVダウンロード

Playwrightの `expect_download` を使ってファイルダウンロードを待ち受けます。

```python
csv_btn = page.get_by_role("link", name="CSVダウンロード").first
csv_btn.wait_for(state="visible", timeout=TIMEOUT["download_ms"])

with page.expect_download(timeout=TIMEOUT["download_ms"]) as dlinfo:
    csv_btn.dispatch_event("click")

download = dlinfo.value
save_path = out_dir / f"{now_stamp()}_{download.suggested_filename}"
download.save_as(str(save_path))
```

`dispatch_event("click")` を使っているのは、通常の `.click()` だとブラウザのデフォルト動作（新規タブで開くなど）が発生するケースがあるためです。

### 4. エラー時のスクリーンショット

各ステップでエラーが発生した場合、自動でスクリーンショットを保存します。後から何が起きたか確認できるので、デバッグ効率が上がります。

```python
def safe_shot(page, tag, out_dir):
    path = out_dir / f"{now_stamp()}_{tag}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
        return path
    except Exception:
        return None
```

## 使い方

### 引数にURLを渡す

```bash
python app.py https://plug.connpass.com/event/381240/
```

### 引数なしで実行（対話モード）

```bash
python app.py
```

`config.toml` に登録したURLから選択できます。

```
登録済みイベント:
  1) https://plug.connpass.com/event/381240/
  0) 手入力
番号を選択 (Enter で 1):
```

## 動作の流れ

```
1. ブラウザ起動
2. イベントページへアクセス
3. ログイン済み？ → Yes: 次へ / No: 手動ログイン待ち
4. 「申込者を管理する」クリック
5. 管理画面で「CSVダウンロード」クリック
6. ~/Downloads/connpass_csv/{イベントID}/ に保存
7. ブラウザ終了
```

## まとめ

| 項目 | 内容 |
|------|------|
| 言語 | Python 3.11+ |
| ライブラリ | Playwright |
| 認証方式 | 手動ログイン待機（OAuth対応） |
| 設定管理 | TOML |
| エラー処理 | 各ステップでスクショ保存 |

Playwrightは `get_by_role` や `expect_download` など、ブラウザ操作に特化したAPIが充実していて書きやすかったです。connpassに限らず、ログインが必要なサイトの定型操作を自動化するパターンとして応用できると思います。
