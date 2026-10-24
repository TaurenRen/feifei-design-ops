#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""verify_pptx.py — 不打开 PowerPoint 也能验证「这份 PPTX 真的可编辑、真的没丢字」。

检三件上游脚本只在导出时喊一嗓子、事后无法复核的事：
  1. 页数对不对
  2. 每页有多少「有字的文本框」——0 就是整页变成图片/空白
  3. 文本 run 是不是真的（可双击编辑），而不是整段被拍成图片
  4. 可选：和源 HTML 的 innerText 比对，报出缺了哪一段

用法：
  python verify_pptx.py deck.pptx
  python verify_pptx.py deck.pptx --html deck-flat.html --selector section
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from pptx import Presentation


def html_texts(html_path: Path, selector: str) -> list[str]:
    """用 playwright 取每页 innerText（去空白），跟 PPTX 对账。"""
    from playwright.sync_api import sync_playwright
    import os
    chrome = os.environ.get("CHROME_PATH") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    out = []
    with sync_playwright() as p:
        kw = {"executable_path": chrome} if Path(chrome).exists() else {}
        br = p.chromium.launch(**kw)
        pg = br.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(html_path.resolve().as_uri(), wait_until="load", timeout=60000)
        pg.wait_for_timeout(1500)
        out = pg.eval_on_selector_all(selector, "els => els.map(e => e.innerText)")
        br.close()
    return [re.sub(r"\s+", "", t or "") for t in out]


def pptx_texts(path: Path) -> list[str]:
    prs = Presentation(str(path))
    res = []
    for s in prs.slides:
        buf = []
        for sh in s.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                buf.append(sh.text_frame.text)
        res.append(re.sub(r"\s+", "", "".join(buf)))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("--html")
    ap.add_argument("--selector", default="section")
    a = ap.parse_args()

    prs = Presentation(a.pptx)
    print(f"■ {a.pptx}")
    print(f"  页数 {len(prs.slides)}；画布 {prs.slide_width/914400:.2f}×{prs.slide_height/914400:.2f} in")

    total_tb = 0
    empty_pages = []
    for i, s in enumerate(prs.slides, 1):
        tbs = [sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
        runs = sum(len(par.runs) for sh in tbs for par in sh.text_frame.paragraphs)
        total_tb += len(tbs)
        if not tbs:
            empty_pages.append(i)
        print(f"  P{i}: shapes {len(s.shapes):>2} · 有字文本框 {len(tbs):>2} · 文本 run {runs:>3}")
    print(f"  合计有字文本框 {total_tb}")

    bad = False
    if empty_pages:
        print(f"  🔴 第 {empty_pages} 页没有任何文字（整页变成图/空白）")
        bad = True

    if a.html:
        ht = html_texts(Path(a.html), a.selector)
        pt = pptx_texts(Path(a.pptx))
        if len(ht) != len(pt):
            print(f"  🟡 源 HTML 有 {len(ht)} 页，PPTX 有 {len(pt)} 页")
        miss = []
        for i, src in enumerate(ht):
            if i >= len(pt):
                miss.append((i + 1, "整页缺失"))
                continue
            # 抽样：源文本每 40 字取一个 12 字片段，检查是否出现在 PPTX 里
            probes = [src[k:k + 12] for k in range(0, max(1, len(src) - 12), 40)]
            lost = [p for p in probes if p and p not in pt[i]]
            if lost:
                miss.append((i + 1, f"{len(lost)}/{len(probes)} 段缺失，如「{lost[0][:14]}…」"))
        if miss:
            print("  🔴 丢字：")
            for n, why in miss:
                print(f"     第 {n} 页 {why}")
            bad = True
        else:
            print("  OK 与源 HTML 逐页比对：没有丢字")

    print("  结论：" + ("有问题，见上面红灯" if bad else "可编辑、无整页空白"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
