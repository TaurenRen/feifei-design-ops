#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""rec_harness.py — 实测取证录屏（真 cmd 窗口跑真命令 / 真 Chrome 浏览产物）。

两类镜头：
  clip_cmd(name, lines)  真实 cmd 窗口执行真实命令（命令逐条 echo + 停顿，画面里看得到）
  clip_web(name, url, plan)  真实 Chrome（Playwright headed）打开产物并滚动/点击，同步截图

都用 ddagrab 抓主屏 1920x1080。录完做 motion_score 验活，定格自动换 gdigrab 重录。

用法示例（import 后调用，或 python harness.py selfcheck）：
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.environ.get("DESKTOP_REC_SCRIPTS") or r"D:\WorkBuddy\.workbuddy\skills\desktop-recording\scripts")
import desktop_rec as dr  # noqa: E402

dr.CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

PROJ = Path(os.environ.get("REC_WORKDIR") or r"D:\hstest")   # 必须是全 ASCII 路径
REC = PROJ / "recordings"
SHOT = PROJ / "screenshots"
TMP = PROJ
HD = Path(os.environ.get("HUASHU_DIR") or r"D:\WorkBuddy\.workbuddy\skills\huashu-design")
PY = r"D:\WorkBuddy\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
NODE = r"D:\WorkBuddy\.workbuddy\binaries\node\versions\22.22.2-6\node.exe"

REC.mkdir(parents=True, exist_ok=True)
SHOT.mkdir(parents=True, exist_ok=True)

u = ctypes.windll.user32


# ── 窗口前台 ────────────────────────────────────────────────────────────────
def pin_topmost(hwnd: int) -> None:
    """最大化 + 置顶。不置顶时 WorkBuddy 主窗口会在我发工具调用时抢焦点，
    录出来的画面就变成 IDE 而不是被测窗口（第一次 selfcheck 就是这么翻的）。"""
    u.ShowWindow(hwnd, 3)                     # SW_MAXIMIZE
    HWND_TOPMOST, SWP_SHOWWINDOW = -1, 0x0040
    SWP_NOSIZE, SWP_NOMOVE = 0x0001, 0x0002
    u.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                   SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW)


def fg_title_contains(needle: str, retries: int = 6) -> bool:
    """按标题包含关系把窗口拉到前台并置顶（ALT 键解锁 + AttachThreadInput 三板斧已内建）。"""
    for i in range(retries):
        ok = _fg_once(needle)
        if ok:
            return True
        time.sleep(0.6)
    return False


def _fg_once(needle: str) -> bool:
    hwnd = None

    def cb(h, _):
        nonlocal hwnd
        n = u.GetWindowTextLengthW(h)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, buf, n + 1)
            if needle in buf.value and u.IsWindowVisible(h):
                hwnd = h
                return False
        return True

    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    u.EnumWindows(CB(cb), 0)
    if not hwnd:
        return False
    ok = dr.force_foreground(hwnd)
    if ok:
        pin_topmost(hwnd)
    return ok


# ── 镜头 1：真实 cmd 窗口跑真实命令 ─────────────────────────────────────────
CMD_HEAD = r"""@echo off
chcp 65001 >nul
title {title}
cd /d {cwd}
color 0A
echo.
echo ============================================================
echo   {title}
echo ============================================================
echo.
"""


def _write_cmd(name: str, lines: list[tuple[str, float]], cwd: str, title: str) -> Path:
    """lines: [(shell 行, 该行之后停顿秒数)]；'@REM' 开头当章节标题 echo。"""
    p = Path(cwd) / f"_{name}.cmd"
    def hold(sec: float) -> str:      # ping -n N 实际停 N-1 秒
        return f"ping -n {int(sec) + 1} 127.0.0.1 >nul\n"
    body = [CMD_HEAD.format(title=title, cwd=cwd)]
    for line, pause in lines:
        if line.startswith("@REM "):
            body.append(f"echo.\necho --- {line[5:]} ---\n")
            body.append(hold(pause))
        else:
            body.append(f"echo ^> {line}\n")
            body.append(f"{line}\n")
            body.append(hold(pause))
    body.append("echo.\necho [done]\n")
    body.append(hold(2))
    body.append("exit\n")
    p.write_text("".join(body), encoding="utf-8")
    return p


def clip_cmd(name: str, lines, title: str, cwd: str = str(TMP), extra_wait: float = 0.0):
    """录一段 cmd 执行。lines = [(命令行, 停顿)] 或 [('@REM 章节标题', 1.0)]"""
    out = REC / f"{name}.mp4"
    bat = _write_cmd(name, lines, cwd, title)
    total = sum(p for _, p in lines) + 1.2 * len(lines) + 12 + extra_wait

    def action():
        sh = subprocess.Popen(
            f'cmd.exe /c "{bat}"',
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            cwd=cwd,
        )
        time.sleep(0.8)
        fg_title_contains(title)
        try:
            sh.wait(timeout=total)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/PID", str(sh.pid), "/T", "/F"],
                           capture_output=True)
        time.sleep(0.6)

    be, score = dr.record_with_fallback(out, action, min_motion=2.0)
    print(f"[clip_cmd] {name} -> {out.name} backend={be} motion={score:.2f}%", flush=True)
    return out, be, score


def pg_scroll(pg, total, seconds, steps=50):
    """Playwright 版匀速滚动（desktop_rec.smooth_scroll 是 selenium 版，用不了）。"""
    per, gap = total / steps, seconds / steps
    for _ in range(steps):
        pg.evaluate(f"window.scrollBy({{top:{per},behavior:'instant'}})")
        time.sleep(gap)


# ── 镜头 2：真实 Chrome 打开产物 ────────────────────────────────────────────
def clip_web(name: str, url: str, plan, title_hint: str = ""):
    """plan: [('wait',3) ('scroll',1200,4) ('shot','xx') ('hover'/'focus',...)]"""
    out = REC / f"{name}.mp4"
    from playwright.sync_api import sync_playwright

    def action():
        with sync_playwright() as p:
            br = p.chromium.launch(
                headless=False,
                executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                args=["--window-position=0,0", "--window-size=1600,1000",
                      "--disable-features=CalculateNativeWinOcclusion",
                      "--disable-backgrounding-occluded-windows"],
            )
            pg = br.new_page(viewport={"width": 1600, "height": 980})
            pg.goto(url, wait_until="load", timeout=60000)
            time.sleep(1.2)
            fg_title_contains(title_hint or pg.title()[:20])
            for step in plan:
                kind = step[0]
                if kind == "wait":
                    time.sleep(step[1])
                elif kind == "goto":
                    pg.goto(step[1], wait_until="load", timeout=60000)
                    time.sleep(step[2] if len(step) > 2 else 1.8)
                elif kind == "scroll":
                    _, dist, secs = step
                    pg_scroll(pg, dist, secs)
                elif kind == "jump":
                    pg.evaluate(f"window.scrollTo(0,{step[1]})")
                    time.sleep(step[2])
                elif kind == "shot":
                    pg.screenshot(path=str(SHOT / f"{step[1]}.png"))
                elif kind == "click":
                    try:
                        pg.click(step[1], timeout=4000)
                    except Exception:
                        pass
                    time.sleep(step[2] if len(step) > 2 else 1.5)
                elif kind == "eval":
                    pg.evaluate(step[1])
                    time.sleep(1.0)
            time.sleep(0.8)
            br.close()

    be, score = dr.record_with_fallback(out, action, min_motion=1.5)
    print(f"[clip_web] {name} -> {out.name} backend={be} motion={score:.2f}%", flush=True)
    return out, be, score


def shot_file(src_html: Path, out_png: Path, width=1440, height=900, full=False):
    """静默截图（不进录屏，用于归档）。"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        pg = br.new_page(viewport={"width": width, "height": height})
        pg.goto(src_html.resolve().as_uri(), wait_until="load", timeout=60000)
        time.sleep(1.5)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(out_png), full_page=full)
        br.close()
    return out_png


if __name__ == "__main__":
    dr.dpi_aware()
    print("screen", dr.screen_size(), "proj", PROJ, "workdir_ok", TMP.is_dir())
    if len(sys.argv) > 1 and sys.argv[1] == "selfcheck":
        (TMP / "selfcheck.txt").write_text("harness ok", encoding="utf-8")
        clip_cmd("selfcheck", [("@REM SELF CHECK", 1.5),
                               ("echo hello huashu", 1.5),
                               ("dir /b", 2.0)], "SELFCHECK harness")
