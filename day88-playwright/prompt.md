# connpass CSVダウンローダー 生成プロンプト

以下のプロンプトをAI（Claude等）に渡すと、同等のコードを再現できます。

---

## プロンプト

```
Playwright（同期API）を使って、connpassイベントの申込者CSVを自動ダウンロードする
Pythonスクリプトを作ってください。

### ゴール
connpassのイベントページから「申込者を管理する」→ 管理画面の「CSVダウンロード」を
実行し、CSVをローカル保存する。

### 要件（必須）
- Python 3.11+（tomllib使用）
- playwright.sync_api（同期）を使用
- 構成は app.py（1ファイルで全処理） + config.toml
- イベントURLは CLI引数 or config.toml から取得
- 引数なし時は config.toml の events.urls から番号選択 or 手入力
- headless はデフォルト false（手動ログインがあるため）
- connpassのURLはサブドメイン付き（例: plug.connpass.com, osaka.connpass.com）なので、
  URLバリデーションの正規表現で必ずサブドメインを許容すること
  - 正: r"^https?://.*connpass\.com/event/\d+/?$"
  - 誤: r"https?://connpass\.com/event/\d+"（サブドメインなしだとマッチしない）

### ログイン（手動ログイン対応）
- ログイン済み判定は「申込者を管理する」リンクが見えるかどうか
  - page.get_by_role("link", name="申込者を管理する").first を使う
- まず短時間（login_check_ms=2000ms）の wait_for で判定し、見つかればそのまま進む
- PWTimeoutError になったら、ログイン画面かどうかをゆるく検知して
  コンソールにメッセージを出し、最大 login_wait_ms=300000ms（5分）wait_for で待つ
- ログイン画面のゆるい検知（is_login_page関数）:
  - 以下の4パターンを候補として、いずれかが visible なら True:
    1. get_by_role("button", name=re.compile(r"ログイン|Login", re.I))
    2. get_by_role("link", name=re.compile(r"ログイン|Login", re.I))
    3. page.locator("form:has-text('ログイン')")
    4. page.locator("input[type='password']")
  - 各候補は try-except で囲み、見つからなくてもスキップする

### 画面遷移
- ensure_logged_in_and_get_manage_link の中で page.goto() を実行する
  （gotoとログイン判定を1つの関数にまとめる）
- 「申込者を管理する」リンクを .click() して管理画面へ遷移
- 管理画面で「CSVダウンロード」リンクを押す

### CSVダウンロード（重要）
- まず csv_btn.wait_for(state="visible") でボタンの表示を待ってから操作する
- expect_download を必ず使ってダウンロードを待ち受ける
- クリックは dispatch_event("click") を使う
  - 理由：通常の .click() だと新規タブが開く/クリックがブロックされるケースがあるため
- download.failure() でダウンロード失敗を検知する
- 保存ファイル名は「YYYYmmdd_HHMMSS_ffffff_」+ download.suggested_filename
- 保存先は config.toml の base_dir / イベントID（URLから正規表現で抽出）

### セレクタ方針
- get_by_role を優先する（文言一致で日本語UIに対応）
- 各要素は単一セレクタで取得し、.first で最初の一致を使う
- ログイン画面の検知のみ、複数パターンをOR判定で試す

### エラー処理
- 各ステップ（ログイン判定、管理画面遷移、CSVダウンロード）を try-except で囲む
- 失敗時は必ずフルページスクリーンショットを _errors ディレクトリに保存する
  （safe_shot関数として切り出し、スクショ自体の失敗も握りつぶす）
- スクショ名は「YYYYmmdd_HHMMSS_ffffff_<tag>.png」
  - tag例：ensure_login_failed, manage_click_failed,
    csv_or_download_timeout, download_failure, download_exception
- 例外メッセージとスクショのパスをコンソールに print する

### 設定ファイル config.toml（外出し）
- paths.base_dir = "~/Downloads/connpass_csv"（expanduserで展開）
- paths.error_dir = "_errors"（base_dir配下）
- browser.headless = false
- timeout.page_load_ms = 60_000
- timeout.login_wait_ms = 300_000
- timeout.login_check_ms = 2_000
- timeout.download_ms = 60_000
- events.urls = ["https://..."]（複数登録可）

### 関数構成
- load_config(): TOML読み込み
- now_stamp(): タイムスタンプ文字列（%Y%m%d_%H%M%S_%f）
- extract_event_id(url): URLから /event/(\d+) を正規表現で抽出。
    マッチしなければ ValueError を送出する（None を返さない）
- validate_event_url(url): URLの形式チェック
- safe_shot(page, tag, out_dir): エラー時スクショ保存
- is_login_page(page): ログイン画面のゆるい検知
- ensure_logged_in_and_get_manage_link(page, event_url, timeout_ms=None):
    内部で page.goto() を実行し、2段階待機のログイン判定後、
    manage_linkのLocatorを返す。timeout_ms省略時はconfig値を使用
- download_connpass_csv(event_url, headless): メイン処理、保存パスを返す
- choose_event_url(): 引数なし時のURL選択UI
- __main__: CLI引数 or choose_event_url() → download_connpass_csv()

### 実装上の注意
- browser.new_context(accept_downloads=True) にする
- download_connpass_csv は成功時に Path を返し、失敗時に None を返す
- __main__ では戻り値で sys.exit(0 or 1) する
- 依存は playwright のみ（tomllib は標準ライブラリ）
```
