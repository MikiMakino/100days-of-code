import yaml
from config import LAYOUTS_DIR


def get_layout_files() -> list[str]:
    """layouts/ フォルダの YAML ファイル名一覧（拡張子なし）を返す"""
    return sorted(f.stem for f in LAYOUTS_DIR.glob("*.yaml"))


def load_layout(name: str) -> dict:
    """指定名のレイアウト定義を読み込んで返す"""
    path = LAYOUTS_DIR / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
