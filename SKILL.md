---
name: huashu-design-ops
description: 花叔 huashu-design（3.0）在本机的落地与加固层：开工前环境体检与修复、把 CLI 真正跑通、修单文件 deck 导 PPTX 丢字、动效渲染兜底、交付前产物复核、录屏取证。触发词：huashu-design、花叔设计、三方向门、design_lint、外观账本、pptx_from_rendered、ref_board、导出的 PPT 丢字、deck-stage 导出、render-video 报错、No webm produced、设计体检红灯、实测一个 agent skill。
metadata:
  upstream: "alchaincyf/huashu-design 3.0.0"
  upstream_license: "MIT"
  tested_on: "Windows 11 + Chrome 141 + Python 3.13 + Node 22.22.2，2026-10-24"
  tested_scope: "网页 / deck+PDF+PPTX / 信息图 / App 原型 / 6s 动效 / 三件事 / 参考板 / 84 风格库 / 体检 / 账本"
---

# huashu-design 落地层 · ops

上游 `huashu-design` 是设计方法论 skill（怎么想、怎么过三方向门、怎么体检）。
这份是**跑起来的那层**：环境、CLI 真实参数、导出链的坑、交付前复核、取证。

**分工**：接到设计任务 → 先装上游并按上游 SKILL.md 做设计；**要动手跑命令、导出、验收时读这份**。
上游没装：`git clone` 被墙时用 codeload 下 tar.gz（见 `references/setup.md`）。

## 开工先跑体检（30 秒）

```bash
python scripts/doctor.py --skill <huashu-design 安装目录>
```

一次报出六件事，缺哪个给哪条修复命令：Chrome 路径、python 侧 playwright+chromium、
node 侧 playwright 及其**自己那份** chromium、node 侧 ffmpeg、上游 skill 目录完整性、ms-playwright 版本目录。

`--fix` 会把本机已有的 ffmpeg/chromium 复制或联接成 node 侧要的版本号（不下载）。
**node 侧和 python 侧的浏览器/ffmpeg 版本号互不相干**——这是本机上 80% 的「导出莫名报错」的真因。

## 三条命令的真实参数（照上游 SKILL.md 抄会连错三次）

```bash
# 1) 记一条偏好：--topics / --evidence 都是必填，且正文必须含用户原话「…」
python <HD>/scripts/learn.py add --kind preference \
  --topics "封面 巨字 色块" --project myproject \
  --evidence "2026-10-24 实测 A/B 对比" \
  "用户原话：「这个完全不 AI 感」。巨字敢放到 148px（适用范围：说明页封面区，不外溢到 App）"

# 2) 记外观账（这条和上游写的一致）
python <HD>/scripts/design_lint.py ledger add out.html --project myproject --note "Collins · 巨字+三色"

# 3) 开工查账（一致）
python <HD>/scripts/design_lint.py ledger
```

`learn.py` 的三个硬性校验：必须 `--topics`、必须 `--evidence`、preference 里必须有「…」引号包住的原话。
少任何一个都直接报错退出——不是警告。范围（适用范围）写进正文，回读时会一起带出来。

## 导出链：三条路各自的地雷

| 要什么 | 命令 | 地雷 |
|---|---|---|
| PDF | `node <HD>/scripts/export_deck_stage_pdf.mjs --html deck.html --out deck.pdf` | 单文件 deck-stage 必须用这个（`export_deck_pdf.mjs` 只适用于多文件）；node 侧缺 chromium 直接崩 |
| 可编辑 PPTX | `python <HD>/scripts/pptx_from_rendered.py deck-flat.html -o deck.pptx --selector "section" --bg f6f4ef` | **必须先 flatten**，见下 |
| MP4 | `python scripts/render_frames.py anim.html --out anim.mp4` | 上游 `render-video.js` 在本机稳定报 `No webm produced` |

### 单文件 deck 导 PPTX 必踩：4/5 页丢字

deck-stage 的 shadow CSS 把非 active 的 `<section>` 设成 `display:none`，量坐标的脚本量不到它们，
于是只有当前页有文字，其余页只剩装饰形状。**上游的丢字校验能报出来，但不给修法**：

```
--selector "deck-stage section"  → 文本框 5 个，5 页里 4 页丢字
flatten 后 --selector "section"  → 文本框 55 个，0 丢字
```

```bash
python scripts/flatten_deck.py deck.html -o deck-flat.html
python <HD>/scripts/pptx_from_rendered.py deck-flat.html -o deck.pptx --selector "section" --bg f6f4ef
python scripts/verify_pptx.py deck.pptx --html deck-flat.html --selector section
```

`flatten_deck.py` 做三件事：换掉 `<deck-stage>` 外壳、移除 `deck_stage.js`、把 section 的
`display:none` 改成 `flex`。`verify_pptx.py` 事后复核页数 / 有字文本框 / 文本 run，并和源 HTML 逐页
抽样比对，把「哪一页缺哪一段」指出来。

### 可编辑 ≠ 1:1 保真（必须提前和用户说清）

实测同一份 deck：PDF 是 1:1，PPTX 会重排。原因两层：
1. `--font-ea` 默认微软雅黑，设计用的 Google Fonts 字体（思源宋体 / Inter）在收件人机器上多半没有 → 字宽全变；
2. 文本框宽度来自渲染时量到的 rect，字体一换就挤或撞。

对策按投入排序：① 把设计字体装进系统并传 `--font-ea`；② 短标签一律 `white-space:nowrap`，别指望 PPT 里自己折行；
③ 对外的「定稿」给 PDF，「可编辑」给 PPTX 并说明是近似版。

### 动效渲染兜底

`render-video.js` 走 Playwright recordVideo，本机（Chrome 141 + 虚拟显卡）三次都是
`Ready at ... → No webm produced`，一行都没录出来。改用逐帧截图：

```bash
python scripts/render_frames.py anim.html --out anim.mp4 --duration 6 --fps 30 --width 1920 --height 1080
```

HTML 契约（三行就够）：

```js
window.__step  = () => { /* 推进一帧演算并绘制 */ return true; };
window.__setT  = (t) => { /* 按第 t 秒设定文字/元素状态 */ return true; };
document.fonts.ready.then(() => requestAnimationFrame(() => { window.__ready = true; }));
```

优点：确定性（同 HTML 同输出，不靠 wall clock）、不依赖 recordVideo、帧序列可当验收素材。
代价：180 帧约 43 秒（1920×1080），比 recordVideo 慢。

## 交付前复核（别只看截图）

```bash
python <HD>/scripts/design_lint.py check out.html            # 🔴 必修 / 🟡 删模板装饰 / ℹ️ 外观家族仅提示
python <HD>/scripts/design_lint.py compare dir-*.html        # 三版撞没撞
python <HD>/scripts/design_lint.py ledger check dir-*.html   # 和最近项目撞没撞
python scripts/verify_pptx.py deck.pptx --html deck-flat.html # PPTX 有没有整页变图
```

判据口径（实测总结）：
- `check` 的 🔴 是可读性底线（正文 ≥14px / 标签 ≥12px / 对比度 ≥4.5），**任何风格都不豁免**。
  想要 HUD 微字或密排小字，就得把字号抬上去再谈风格——这是这类风格在体检里的必然红灯。
- `compare` 的「色板距离」对同属浅色的两版很敏感：暖纸 `#F4F1EA` vs 灰纸 `#DDD7CC` 只有 0.026，
  判为撞版。加面积大的色块、或换纸色到 0.146 以上才过。**不要靠改一个色号糊过去**。
- 三版都落进同一个外观家族（如「细线报纸」）只是 🟡 提示；科学说明页这类题材可以留，但要在交付说明里写理由。

## 取证（要给人看「我真跑过」时）

`scripts/rec_harness.py` 提供两个镜头：`clip_cmd`（真 cmd 窗口跑真命令）与 `clip_web`（真 Chrome 浏览产物），
ddagrab 抓 1920×1080，录完用运动度验活，定格自动换 gdigrab 重录。三条硬规矩来自实测：
窗口必须**最大化 + 置顶**（否则录到的是后台 IDE）、cmd 窗口路径必须全 ASCII、批处理里 `chcp 65001` 才能传中文参数。

## 关联

- 上游设计方法论：`huashu-design`（三方向门、风格库、体检口径）——这份只管跑通与复核
- 上游 `capabilities.py` 只扫 `~/.claude/skills` 等目录，**不认 WorkBuddy 的 `~/.workbuddy/skills`**，
  所以「兄弟 skill」「素材档位」会一律报 T0/无。以实际能力为准，别被它的输出带偏。
- 详细踩坑与证据：`references/pitfalls.md`；安装与版本对齐：`references/setup.md`
- 实测报告与录屏：仓库 `report/实测报告.md`、`report/recordings/`
