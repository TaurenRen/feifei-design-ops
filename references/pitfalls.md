# 踩坑清单（12 条，全部本机实测）

环境：Windows 11 · Chrome 141 · Python 3.13.12（venv）· Node 22.22.2 · huashu-design 3.0.0（master，2026-10-23 commit）

---

## A. 安装

**1. `git clone github.com` 直接失败（curl 28 连接超时），codeload 可用。**
```
git clone → RPC failed; curl 28 Failed to connect to github.com:443
curl -L https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/master  → 200，37 MB
```
安装就绪的最短路径：codeload 下 tar.gz 解到 `~/.workbuddy/skills/huashu-design`，再 `npm install`。
`gh api` 走的是 api.github.com，同样是通的——被挡的只是 git/https 直连。

**2. python 侧与 node 侧的 playwright 各要一份浏览器，版本号还不一样。**
- python playwright → `ms-playwright/chromium-1248`
- 上游 `node_modules/playwright` 1.59.1 → 要 `chromium-1217`（headless shell 同理）
- 上游 `render-video.js` 还要 `ms-playwright/ffmpeg-1011`，而 python 侧给的是 `1013`

症状全是同一句：`Executable doesn't exist at ...ms-playwright/chromium-1217...`，很容易误判成网络问题。
`doctor.py --fix` 用目录联接把版本号补齐（不下载），或 `cd <skill> && npx playwright install chromium ffmpeg`
（本机实测这条下载会被限速，20 分钟量级）。

**3. `capabilities.py` 的目录清单不认 WorkBuddy。**
它只扫 `~/.claude/skills`、`~/.agents/skills`、`~/.codex/skills`、`~/.cursor/skills`、`.claude/skills`、`.agents/skills`。
本机技能在 `~/.workbuddy/skills` → 「兄弟 skill：没有」「素材档位：T0」是**假阴性**，别据此降级素材方案。

---

## B. 命令与脚本

**4. `learn.py add` 有三个必填，上游 SKILL.md 一个都没写。**
少 `--topics` → 报 required；少 `--evidence` → 报「没人能核对的条目只是传言」；
preference 正文里没有「…」包住的用户原话 → 报「必须引用用户原话」。三次报错，三次改命令。

**5. `ref_board.py` 会截到「加载中」。**
ncase.me 那张板截下来是 `loading... 7%`：脚本等的是 `networkidle`（8 s 上限），
而这类站点的首屏是 JS 驱动的分步加载，networkidle 之后还在转圈。
对策：对带 loading 的站点手工加 `--full` 或换同作品的图片/报道页；把「截到的是不是加载中」当成必检项。

**6. 单文件 `<deck-stage>` deck 导 PPTX，5 页里 4 页丢字。**
`--selector "deck-stage section"` 只量到当前页。修法见 `SKILL.md`「flatten」段。
上游脚本的丢字校验**报得很准**（"4 处文字在浏览器里看得见、PPTX 里没有"），只是不给修法。

**7. `render-video.js` 在本机稳定 `No webm produced`。**
试过：bundled chromium、channel:chrome、补 ffmpeg 1011——三次都在 `Ready at 1.25s` 之后失败，
TMP_DIR 里没有任何 .webm。recordVideo 这条路在本机不可用，换 `render_frames.py`。

**8. `assets/deck_stage.js` 里的 CSS 会压过 print 媒体查询，`page.pdf()` 永远只有 1 页。**
这是上游已知并已处理的问题（`export_deck_stage_pdf.mjs` 会把 section 拔出 slot），
所以别自己写 `page.pdf()`，直接用那个脚本。

---

## C. 体检口径

**9. 可读性底线会否掉「微字美学」。**
HUD 式 11px 等宽标签、杂志式 10px 图注，`design_lint check` 一律 🔴。
本机实测：dir-1 有 23 处标签低于 12px、dir-3 有 24 处。抬到 12/14px 后全绿，
但「仪器读数感」会弱一档——这是必须提前和用户交代的取舍，不是 bug。

**10. `compare` 的色板距离对同明度不同色相不敏感。**
暖纸 `#F4F1EA` 与灰纸 `#DDD7CC` 距离 0.026 → 判撞版；加三色大面积色块只到 0.039；
最后是换到牛皮纸 `#CDBFA4` + 中明度底色 `#B9AB90` 才到 0.146 过线。
**结论：撞版要靠换骨架或换材料，改一个色号糊不过去——这一点上游说对了，但阈值给人的直觉是反的。**

**11. 三版全在同一个「外观家族」是 🟡 不是 🔴。**
本机三版最终都带 1px 细线 + 零圆角（「细线报纸」家族）。科学说明页题材下这是合理选择，
按上游口径只需在交付说明里写明理由，不必为消黄灯去改结构。

---

## D. 内容

**12. 事实核实真的会抓错。**
Boids 题材里最容易被写错的是年份：Reynolds 的论文是 **SIGGRAPH 1987**（Computer Graphics 21(4), 25–34），
常被写成 1986（1986 是演示视频的年份）。本机按上游「第一步先 WebSearch」核到 SIGGRAPH 历史档案原文才写。
同理，「凝聚拉满 → 漩涡」这个说法在纯三条规则、无外力、周期边界下**不成立**：
实测 6 组权重，最强的一组也只到「收成一团 + 边缘打转」。
要真漩涡需要额外机制（中心吸引点 / 边界反弹 / 持续不对称推力）。文案已按实测改写。
