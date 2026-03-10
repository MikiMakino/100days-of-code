"""config.py - プロファイル保存・読み込み"""

import os
import json

PROFILE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ftp_profile.json")


def load_profile():
    """接続プロファイルをJSONから読み込む。ファイルがなければNoneを返す。"""
    if not os.path.exists(PROFILE_FILE):
        return None
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_profile(host, port, user, passwd, passive):
    """接続プロファイルをJSONに保存する。"""
    profile = {
        "host":    host,
        "port":    port,
        "user":    user,
        "passwd":  passwd,
        "passive": passive,
    }
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    return PROFILE_FILE
