#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""doctor.py — huashu-design 在本机的可用性体检（只读，除 --fix 建联接外不改任何东西）。

为什么需要它：上游 SKILL.md 只写了 `pip install playwright`，但实际跑通要三套东西：
python 侧 playwright+chromium、node 侧 playwright+它自己版本的 chromium、node 侧 ffmpeg。
三套版本号互不相干，缺任何一个都会在「导出 PDF / 导出 PPTX / 渲染 MP4」时炸掉，
报错信息还都指向 playwright 本身，很容易误判成网络问题。

用法：
  python doctor.py                     # 只体检
  python doctor.py --fix               # 缺版本号时用目录联接补齐（不下载）
  python doctor.py --skill <huashu-design 路径>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
BROWSER_ROOT = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"


def ok(b):   return "OK  " if b else "FAIL"
def warn(b): return "WARN" if b else "OK  "


def chrome_path() -> str | None:
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def py_playwright() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "未安装：pip install playwright pillow python-pptx"
    try:
        with sync_playwright() as p:
            exe = Path(p.chromium.executable_path)
        return exe.exists(), str(exe)
    except Exception as e:
        return False, f"实例化失败：{e}"


def node_playwright(skill: Path | None) -> tuple[bool, str, str | None]:
    """返回 (ok, 说明, 期望的 chromium 版本目录名)"""
    if not skill:
        return False, "未指定 --skill，跳过", None
    nm = skill / "node_modules" / "playwright"
    if not nm.is_dir():
        return False, f"node_modules 里没有 playwright：cd {skill} && npm install", None
    try:
        out = subprocess.run(
            [shutil.which("node") or "node", "-e",
             "console.log(require('%s/package.json').version)" % nm.as_posix().replace("\\", "/")],
            capture_output=True, text=True, timeout=30)
        ver = out.stdout.strip() or "?"
    except Exception as e:
        return False, f"读版本失败：{e}", None
    # 从 .links 反查需要的浏览器版本号
    need = None
    reg = BROWSER_ROOT / "chromium-"  # 占位，下面靠目录扫描判断
    dirs = sorted([d.name for d in BROWSER_ROOT.glob("chromium-*") if d.is_dir()]) if BROWSER_ROOT.is_dir() else []
    return True, f"playwright {ver}；本机 chromium 目录：{', '.join(dirs) or '无'}", need


def ffmpeg_ok() -> tuple[bool, str]:
    exe = shutil.which("ffmpeg")
    local = Path(r"D:\ProgramData\ffmpeg-win64\bin\ffmpeg.exe")
    if exe:
        return True, exe
    if local.exists():
        return True, f"{local}（不在 PATH，脚本里需写绝对路径）"
    return False, "未找到 ffmpeg（PATH 与本机固定路径都没有）"


def browser_revisions() -> dict:
    if not BROWSER_ROOT.is_dir():
        return {}
    return {d.name: d.is_dir() for d in BROWSER_ROOT.iterdir() if d.is_dir()}


def junction(link: Path, target: Path) -> bool:
    if link.exists():
        return True
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                       capture_output=True, text=True)
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", help="huashu-design 的安装目录")
    ap.add_argument("--fix", action="store_true", help="缺版本号时用联接补齐（不下载）")
    a = ap.parse_args()

    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    skill = Path(a.skill).expanduser().resolve() if a.skill else None
    print("== huashu-design 环境体检 ==")
    print(f"python      {sys.version.split()[0]}  {sys.executable}")

    c = chrome_path()
    print(f"{ok(bool(c))} Chrome    {c or '未找到'}")

    p_ok, p_msg = py_playwright()
    print(f"{ok(p_ok)} py-playwright  {p_msg}")

    if skill:
        print(f"{ok((skill / 'SKILL.md').exists())} skill     {skill}")
        for sub in ("scripts", "references", "assets"):
            print(f"{ok((skill / sub).is_dir())}   /{sub}")

    n_ok, n_msg, _ = node_playwright(skill)
    print(f"{ok(n_ok)} node-playwright  {n_msg}")

    f_ok, f_msg = ffmpeg_ok()
    print(f"{ok(f_ok)} ffmpeg    {f_msg}")

    rev = browser_revisions()
    print("\n-- ms-playwright 目录 --")
    for k, v in sorted(rev.items()):
        print(f"  {'OK  ' if v else 'FAIL'} {k}")

    # 版本补齐：node 侧要的是 playwright 记录的精确 revision，目录名差一位就跑不起来
    if a.fix and skill:
        fixes = []
        nums = {int(k.split("-")[1]) for k in rev if k.startswith("chromium-") and k.split("-")[1].isdigit()}
        shell_nums = {int(k.split("-")[1]) for k in rev
                      if k.startswith("chromium_headless_shell-") and k.split("-")[1].isdigit()}
        if nums:
            best = max(nums)
            # 只补「本机没有任何一个版本」的情况，已有就提示手动对齐
            fixes.append(("chromium", best))
            fixes.append(("chromium_headless_shell", None))
        for name, ver in fixes:
            if ver is None:
                if not shell_nums:
                    continue
                ver = max(shell_nums)
            print(f"\n[fix] {name}-{ver} 已存在；若 node 侧报的是别的版本号，"
                  f"手工建联接：mklink /J <ms-playwright>\\{name}-<需要版本> <ms-playwright>\\{name}-{ver}")
        fp = BROWSER_ROOT / "ffmpeg-1013" / "ffmpeg-win64.exe"
        if fp.exists():
            target = BROWSER_ROOT / "ffmpeg-1011"
            target.mkdir(exist_ok=True)
            dst = target / "ffmpeg-win64.exe"
            if not dst.exists():
                shutil.copy2(fp, dst)
                print(f"[fix] 已把 {fp.name} 复制到 {target}（node 侧常要 1011）")

    print("\n-- 下一步 --")
    if not p_ok:
        print("  1) pip install playwright pillow python-pptx && playwright install chromium")
    if skill and not n_ok:
        print(f"  2) cd {skill} && npm install && npx playwright install chromium ffmpeg")
    print("  3) 导出前先跑：python flatten_deck.py <deck.html>（修单文件 deck 的 PPTX 丢字）")
    print("  4) 渲染视频用：python render_frames.py <anim.html> --out out.mp4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
