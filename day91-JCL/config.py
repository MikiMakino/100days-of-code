from pathlib import Path

# ─── JOBカード固定パラメータ ───────────────────────────────────────────
JOB_CLASS = "A"
JOB_MSGCLASS = "X"
JOB_NOTIFY = "&SYSUID"
JOB_DESCRIPTION = "JCL GENERATOR"

# ─── ディレクトリ ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
LAYOUTS_DIR = BASE_DIR / "layouts"

# ─── SORTOUT DCB 固定値 ───────────────────────────────────────────────
RECFM = "FB"
BLKSIZE = 0
SPACE_UNIT = "CYL"
SPACE_PRIMARY = 10
SPACE_SECONDARY = 5
