from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import config


@dataclass
class Condition:
    field_name: str
    start: int
    length: int
    field_type: str   # "CH" | "PD"
    operator: str     # "EQ" | "NE" | "GT" | "LT" | "GE" | "LE"
    value: str
    connector: str    # "AND" | "OR" | "" (最後の条件は空)


@dataclass
class JCLConfig:
    user_code: str
    input_dsn: str
    output_dsn: str
    lrecl: int
    conditions: list[Condition]
    output_mode: str            # "COPY" | "SELECT"
    output_fields: list[dict] = field(default_factory=list)


class JCLGenerator:
    def __init__(self, jcl_config: JCLConfig):
        self.cfg = jcl_config

    def generate(self) -> str:
        lines: list[str] = []
        lines += self._job_card()
        lines += self._step()
        lines += self._sysin()
        return "\n".join(lines)

    # ─── JOBカード ──────────────────────────────────────────────────────
    def _job_card(self) -> list[str]:
        uc = self.cfg.user_code.upper()
        return [
            f"//{uc:<8} JOB (ACCT),'{config.JOB_DESCRIPTION}',",
            f"//             CLASS={config.JOB_CLASS},"
            f"MSGCLASS={config.JOB_MSGCLASS},"
            f"NOTIFY={config.JOB_NOTIFY}",
            "//*",
        ]

    # ─── EXEC と DD 文 ───────────────────────────────────────────────────
    def _step(self) -> list[str]:
        out_lrecl = self._calc_output_lrecl()
        return [
            "//STEP1    EXEC PGM=SORT",
            "//SYSOUT   DD SYSOUT=*",
            f"//SORTIN   DD DSN={self.cfg.input_dsn},DISP=SHR",
            f"//SORTOUT  DD DSN={self.cfg.output_dsn},DISP=(NEW,CATLG,DELETE),",
            f"//             SPACE=({config.SPACE_UNIT},"
            f"({config.SPACE_PRIMARY},{config.SPACE_SECONDARY}),RLSE),",
            f"//             DCB=(RECFM={config.RECFM},"
            f"LRECL={out_lrecl},BLKSIZE={config.BLKSIZE})",
        ]

    def _calc_output_lrecl(self) -> int:
        if self.cfg.output_mode == "SELECT" and self.cfg.output_fields:
            return sum(f["length"] for f in self.cfg.output_fields)
        return self.cfg.lrecl

    # ─── SYSIN ──────────────────────────────────────────────────────────
    def _sysin(self) -> list[str]:
        lines = ["//SYSIN    DD *"]
        lines.append("  SORT FIELDS=COPY")
        if self.cfg.conditions:
            lines += self._include_cond()
        if self.cfg.output_mode == "SELECT" and self.cfg.output_fields:
            lines += self._outrec()
        lines.append("/*")
        return lines

    def _format_value(self, cond: Condition) -> str:
        if cond.field_type == "CH":
            padded = cond.value.ljust(cond.length)
            return f"C'{padded}'"
        return f"P'{cond.value}'"  # PD

    def _include_cond(self) -> list[str]:
        # 各条件をトークン化（末尾にコネクタを付ける）
        parts: list[str] = []
        for cond in self.cfg.conditions:
            val = self._format_value(cond)
            token = f"{cond.start},{cond.length},{cond.field_type},{cond.operator},{val}"
            if cond.connector:
                token += f",{cond.connector}"
            parts.append(token)

        indent = " " * 16  # "  INCLUDE COND=(" の文字数に合わせる

        if len(parts) == 1:
            return [f"  INCLUDE COND=({parts[0]})"]

        lines = [f"  INCLUDE COND=({parts[0]},"]
        for i, part in enumerate(parts[1:], 1):
            if i < len(parts) - 1:
                lines.append(f"{indent}{part},")
            else:
                lines.append(f"{indent}{part})")
        return lines

    def _outrec(self) -> list[str]:
        fields_str = ",".join(
            f"{f['start']},{f['length']}" for f in self.cfg.output_fields
        )
        return [f"  OUTREC FIELDS=({fields_str})"]

    # ─── ファイル保存 ────────────────────────────────────────────────────
    def save(self, content: str) -> Path:
        config.OUTPUT_DIR.mkdir(exist_ok=True)
        safe_dsn = self.cfg.output_dsn.replace(".", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_dsn}_{timestamp}.jcl"
        path = config.OUTPUT_DIR / filename
        path.write_text(content, encoding="ascii")
        return path
