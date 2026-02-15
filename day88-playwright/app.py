import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

import tomllib

from playwright.sync_api import (
    Locator,
    Page,
    sync_playwright,
    TimeoutError as PWTimeoutError,
)


# ====== 設定読み込み ======
CONFIG_PATH = Path(__file__).parent / "config.toml"


def load_config() -> dict:
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


CFG = load_config()

BASE_DIR = Path(CFG["paths"]["base_dir"]).expanduser()
BASE_DIR.mkdir(parents=True, exist_ok=True)

ERROR_DIR = BASE_DIR / CFG["paths"]["error_dir"]
ERROR_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = CFG["timeout"]
BROWSER_CFG = CFG["browser"]
EVENT_URLS: list[str] = CFG.get("events", {}).get("urls", [])


# ====== ユーティリティ ======
def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def extract_event_id(event_url: str) -> str:
    """URLからイベントIDを抽出する。マッチしなければ ValueError。"""
    m = re.search(r"/event/(\d+)/?$", event_url)
    if not m:
        raise ValueError(f"イベントIDが抽出できません: {event_url}")
    return m.group(1)


def validate_event_url(event_url: str) -> bool:
    return bool(re.search(r"^https?://.*connpass\.com/event/\d+/?$", event_url))


def safe_shot(page: Page, tag: str, out_dir: Path) -> Optional[Path]:
    path = out_dir / f"{now_stamp()}_{tag}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
        return path
    except Exception:
        return None


def is_login_page(page: Page) -> bool:
    """connpassのログイン画面っぽい特徴をゆるく検知。"""
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


def ensure_logged_in_and_get_manage_link(
    page: Page, event_url: str, timeout_ms: int | None = None
) -> Locator:
    """
    - event_url へ移動
    - ログイン済みなら「申込者を管理する」リンクが短時間で見えるはず
    - 未ログインなら手動ログインを促して、リンクが見えるまで待つ
    """
    if timeout_ms is None:
        timeout_ms = TIMEOUT["login_wait_ms"]

    page.goto(event_url, wait_until="domcontentloaded",
              timeout=TIMEOUT["page_load_ms"])

    manage_link = page.get_by_role("link", name="申込者を管理する").first

    try:
        manage_link.wait_for(state="visible", timeout=TIMEOUT["login_check_ms"])
        return manage_link
    except PWTimeoutError:
        pass

    if is_login_page(page):
        print("ログイン画面を検知しました。ブラウザで手動ログインしてください…")
    else:
        print("ログイン済み判定が取れません（未ログイン/権限/読込中の可能性）。")
        print("必要に応じてブラウザでログインを完了させてください…")

    print("『申込者を管理する』が表示されたら自動で再開します。")
    manage_link.wait_for(state="visible", timeout=timeout_ms)
    return manage_link


# ====== メイン処理 ======
def download_connpass_csv(event_url: str, headless: bool | None = None) -> Optional[Path]:
    """
    connpassイベントの「申込者の管理」→「CSVダウンロード」を実行して保存する。
    """
    if headless is None:
        headless = BROWSER_CFG["headless"]

    if not validate_event_url(event_url):
        print("URLが正しくありません。（例: https://xxx.connpass.com/event/123456/ ）")
        return None

    event_id = extract_event_id(event_url)
    out_dir = BASE_DIR / event_id
    out_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # 1) イベントページへ移動＋ログイン判定
            try:
                manage_link = ensure_logged_in_and_get_manage_link(page, event_url)
            except Exception as e:
                pth = safe_shot(page, "ensure_login_failed", ERROR_DIR)
                print(f"ログイン判定/待機でエラー: {e}\nスクショ: {pth}")
                return None

            # 2) 管理画面へ
            try:
                manage_link.click()
                page.wait_for_load_state("domcontentloaded",
                                         timeout=TIMEOUT["page_load_ms"])
            except Exception as e:
                pth = safe_shot(page, "manage_click_failed", ERROR_DIR)
                print(f"『申込者の管理』クリックに失敗: {e}\nスクショ: {pth}")
                return None

            # 3) CSVダウンロード
            try:
                csv_btn = page.get_by_role("link", name="CSVダウンロード").first
                csv_btn.wait_for(state="visible", timeout=TIMEOUT["download_ms"])

                with page.expect_download(timeout=TIMEOUT["download_ms"]) as dlinfo:
                    csv_btn.dispatch_event("click")

                download = dlinfo.value

                failure = download.failure()
                if failure:
                    pth = safe_shot(page, "download_failure", ERROR_DIR)
                    print(f"ダウンロード失敗: {failure}\nスクショ: {pth}")
                    return None

                filename = f"{now_stamp()}_{download.suggested_filename}"
                save_path = out_dir / filename
                download.save_as(str(save_path))

                print(f"保存完了: {save_path}")
                return save_path

            except PWTimeoutError as e:
                pth = safe_shot(page, "csv_or_download_timeout", ERROR_DIR)
                print(f"タイムアウト（CSVボタン/ダウンロード待機）: {e}\nスクショ: {pth}")
                return None
            except Exception as e:
                pth = safe_shot(page, "download_exception", ERROR_DIR)
                print(f"ダウンロード処理で例外: {e}\nスクショ: {pth}")
                return None

        finally:
            browser.close()


def choose_event_url() -> str:
    """CLIで引数なし実行時、config登録URLがあれば選択肢を表示する。"""
    if not EVENT_URLS:
        return input("connpassのイベントURLを入力してください: ").strip()

    print("登録済みイベント:")
    for i, u in enumerate(EVENT_URLS, 1):
        print(f"  {i}) {u}")
    print("  0) 手入力")

    choice = input("番号を選択 (Enter で 1): ").strip()
    if choice == "" or choice == "1":
        return EVENT_URLS[0]
    if choice == "0":
        return input("URLを入力: ").strip()
    idx = int(choice) - 1
    if 0 <= idx < len(EVENT_URLS):
        return EVENT_URLS[idx]
    print("無効な番号です。手入力に切り替えます。")
    return input("URLを入力: ").strip()


# ====== CLI ======
if __name__ == "__main__":
    url = sys.argv[1].strip() if len(sys.argv) >= 2 else choose_event_url()
    path = download_connpass_csv(url)
    sys.exit(0 if path else 1)
