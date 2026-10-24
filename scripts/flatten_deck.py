#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""flatten_deck.py — 把单文件 <deck-stage> deck 拆成「所有页同时可见」的扁平版，
专治 pptx_from_rendered.py 只导到当前页、其余页大面积丢字。

实测（2026-10-24，5 页 deck）：
  --selector "deck-stage section" → 文本框 5 个，5 页里 4 页丢字
  flatten 后 --selector "section" → 文本框 55 个，0 丢字

原因是 deck-stage 的 shadow CSS 对非 active 的 <section> 做 display:none，
它们在浏览器里没有布局盒，量坐标的脚本自然量不到。

用法：
  python flatten_deck.py deck.html [-o deck-flat.html]
  # 再导出
  python <skill>/scripts/pptx_from_rendered.py deck-flat.html -o deck.pptx --selector "section"
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STAGE_OPEN = re.compile(r"<deck-stage\b[^>]*>", re.I)
STAGE_CLOSE = re.compile(r"</deck-stage>", re.I)


def flatten(html: str) -> tuple[str, list[str]]:
    notes = []

    # 1) 去掉 deck-stage 外壳（换成普通 div，保留尺寸属性不用）
    if STAGE_OPEN.search(html):
        html = STAGE_OPEN.sub('<div class="deck-flat">', html, count=1)
        notes.append("去掉 <deck-stage> 外壳")
    if STAGE_CLOSE.search(html):
        html = STAGE_CLOSE.sub("</div>", html, count=1)

    # 2) 去掉外壳脚本（它会接管导航并强制单页显示）
    if re.search(r'<script[^>]+deck_stage\.js', html, re.I):
        html = re.sub(r'<script[^>]+deck_stage\.js[^>]*>\s*</script>', "", html, flags=re.I)
        notes.append("移除 deck_stage.js")

    # 3) section 一律可见，纵向排布
    html = re.sub(r"(section\s*\{[^}]*?)display\s*:\s*none", r"\1display:flex", html, flags=re.I)
    if re.search(r"section\.active\s*\{[^}]*display\s*:\s*flex", html, re.I):
        html = re.sub(r"section\.active\s*\{[^}]*\}", "body{width:1920px}", html, flags=re.I)
        notes.append("解除 section.active 的显示开关")

    # 4) 保险：给每页一个可见性兜底样式
    style = ("<style>/* flatten: 所有页同时可见，供 PPTX 逐页量坐标 */\n"
             "section{display:flex !important;}\n"
             "body{overflow:visible !important;}\n</style>\n")
    if "</head>" in html:
        html = html.replace("</head>", style + "</head>", 1)
    return html, notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    src = Path(a.html)
    out = Path(a.out) if a.out else src.with_name(src.stem + "-flat" + src.suffix)
    html, notes = flatten(src.read_text(encoding="utf-8"))
    out.write_text(html, encoding="utf-8")
    print(f"→ {out}")
    for n in notes:
        print("  ·", n)
    print(f'  下一步：pptx_from_rendered.py {out.name} -o deck.pptx --selector "section"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
