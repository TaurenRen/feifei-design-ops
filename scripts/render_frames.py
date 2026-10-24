#!/usr/bin/env python
"""render_frames.py — 逐帧渲染 HTML 动画为 MP4（确定性，不依赖 playwright recordVideo）。

为什么需要它：skill 自带的 scripts/render-video.js 走 Playwright recordVideo，
本机环境下（node 侧 playwright 与浏览器/ffmpeg 版本对不上）稳定报 "No webm produced"。
逐帧截图 + ffmpeg 组装不依赖 recordVideo，且帧级可复现。

HTML 契约（两个钩子）：
  window.__step()        推进一帧（演算 + 绘制），返回 true
  window.__setT(t)       设定第 t 秒的文字/元素状态，返回 true
  window.__ready = true  首帧就绪后置位

用法：
  python render_frames.py anim.html --out anim.mp4 --duration 6 --fps 30 \
      [--width 1920] [--height 1080] [--keep-frames]
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

FFMPEG = r"D:\ProgramData\ffmpeg-win64\bin\ffmpeg.exe"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("--out", required=True)
    ap.add_argument("--duration", type=float, default=6.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--keep-frames", action="store_true")
    a = ap.parse_args()

    html = Path(a.html).resolve()
    out = Path(a.out).resolve()
    frames = html.parent / f"_frames_{html.stem}"
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir()

    n = int(round(a.duration * a.fps))
    t0 = time.time()
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path=CHROME, args=["--force-device-scale-factor=1"])
        pg = br.new_page(viewport={"width": a.width, "height": a.height}, device_scale_factor=1)
        pg.goto(html.as_uri(), wait_until="load", timeout=60000)
        pg.wait_for_function("window.__ready === true", timeout=20000)
        for i in range(n):
            pg.evaluate("([t]) => { window.__setT(t); window.__step(); }", [i / a.fps])
            pg.screenshot(path=str(frames / f"f{i:05d}.png"))
        br.close()
    print(f"帧 {n} 张，用时 {time.time() - t0:.1f}s")

    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
           "-framerate", str(a.fps), "-i", str(frames / "f%05d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
           "-movflags", "+faststart", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-800:], file=sys.stderr)
        return 1
    size = out.stat().st_size / 1e6
    print(f"✓ {out}  {size:.2f} MB  {a.width}x{a.height} @{a.fps}fps  {a.duration}s")
    if not a.keep_frames:
        shutil.rmtree(frames, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
