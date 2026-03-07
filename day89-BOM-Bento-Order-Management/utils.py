"""
utils.py - 共通ユーティリティ（締め切り判定・PDF生成）
"""
from datetime import datetime, date
from pathlib import Path
import io


def can_order(order_date: date) -> tuple[bool, str]:
    """注文・キャンセル可否を返す（締め切り制御）"""
    today = date.today()
    if order_date < today:
        return False, "過去の日付には注文できません"
    if order_date == today and datetime.now().hour >= 9:
        return False, "本日9時の締め切りを過ぎています（管理者に連絡してください）"
    return True, ""


def deadline_status() -> tuple[bool, str]:
    """今日の締め切り状況（past=True なら締め切り済み、メッセージ付き）"""
    now = datetime.now()
    today = date.today()
    deadline = datetime(today.year, today.month, today.day, 9, 0)
    if now >= deadline:
        return True, "⚠️ 本日 9:00 の締め切りを過ぎています"
    remaining_min = int((deadline - now).total_seconds() / 60)
    return False, f"⏰ 本日の締め切りまで残り **{remaining_min}分**"


def generate_order_pdf(order_date: str, quantity: int, unit_price: int) -> bytes:
    """発注書 PDF を生成して bytes で返す"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # 日本語フォント登録（Windows / Mac / Linux 対応）
        font_candidates = [
            ("C:/Windows/Fonts/msgothic.ttc", "MSGothic"),
            ("C:/Windows/Fonts/meiryo.ttc", "Meiryo"),
            ("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", "HiraKaku"),
            ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "NotoSans"),
        ]
        jp_font = "Helvetica"
        for path, name in font_candidates:
            if Path(path).exists():
                try:
                    pdfmetrics.registerFont(TTFont(name, path))
                    jp_font = name
                    break
                except Exception:
                    pass

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2.5*cm, rightMargin=2.5*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title", fontName=jp_font, fontSize=18, spaceAfter=6, alignment=1)
        normal_style = ParagraphStyle("normal", fontName=jp_font, fontSize=11, leading=18)
        small_style = ParagraphStyle("small", fontName=jp_font, fontSize=9, textColor=colors.grey)

        issued_at = datetime.now().strftime("%Y年%m月%d日")
        order_fmt = order_date  # YYYY-MM-DD
        total = quantity * unit_price

        elements = [
            Paragraph("お弁当発注書", title_style),
            HRFlowable(width="100%", thickness=2, color=colors.darkblue),
            Spacer(1, 0.5*cm),
            Paragraph(f"発行日：{issued_at}", small_style),
            Spacer(1, 0.8*cm),
        ]

        data = [
            ["項目", "内容"],
            ["お弁当受取日", order_fmt],
            ["発注数量", f"{quantity} 個"],
            ["単価", f"¥{unit_price:,}"],
            ["合計金額", f"¥{total:,}"],
        ]

        col_widths = [5*cm, 10*cm]
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("FONTNAME",    (0, 0), (-1, -1), jp_font),
            ("FONTSIZE",    (0, 0), (-1, -1), 12),
            ("BACKGROUND",  (0, 0), (-1, 0),  colors.darkblue),
            ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
            ("BACKGROUND",  (0, 1), (0, -1),  colors.lightgrey),
            ("GRID",        (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING",     (0, 0), (-1, -1), 8),
            ("ALIGN",       (1, 1), (1, -1),  "LEFT"),
            ("FONTSIZE",    (0, -1), (-1, -1), 14),
            ("TEXTCOLOR",   (0, -1), (-1, -1), colors.darkred),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("以上、よろしくお願いいたします。", normal_style))

        doc.build(elements)
        return buffer.getvalue()

    except ImportError:
        raise RuntimeError("reportlab がインストールされていません: pip install reportlab")


def export_orders_excel(df, year: int, month: int) -> bytes:
    """注文データを Excel で返す"""
    import pandas as pd
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=f"{year}年{month}月")
    return buffer.getvalue()
