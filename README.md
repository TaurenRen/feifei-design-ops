# feifei-design-ops

花叔 [`huashu-design`](https://github.com/alchaincyf/huashu-design) 3.0 的**落地增强层**：让它在你这台机器上真能跑通，并且导出物在交付前能被证明是对的。

上游是设计方法论（三方向门、84 种带样张的风格库、外观账本、设计体检）。这份不重复它的方法论，只补三类东西：

1. **环境体检与修复** —— python 侧 / node 侧两套 playwright + 两套浏览器 + 两套 ffmpeg，版本号互不相干
2. **导出链的坑与修法** —— 单文件 deck 导 PPTX 会丢 4/5 页文字；`render-video.js` 在本机录不出 webm
3. **交付前复核** —— 不靠肉眼看截图，用脚本确认「PPTX 真的可编辑、真的没丢字」

MIT。上游也是 MIT，本仓库只引用不复制上游代码。

---

## 实测结论（Windows 11 · Chrome 141 · Python 3.13 · Node 22.22.2，2026-10-24）

| 上游承诺 | 实测结果 | 说明 |
|---|---|---|
| 网页 / 信息图 / App 原型 / deck 出一页 HTML | ✅ 通 | 六个候选 → 三版完整稿全程走通，`design_lint` 全绿 |
| 84 种风格带样张 | ✅ 通 | 目录实数 20+20+20+12+12 = 84，总览图 ×5 |
| `ref_board.py` 截参考作品 | ⚠️ 半通 | 截得到，但对 JS 分步加载的站点会截到「loading 7%」 |
| 可编辑 PPTX 导出 | ⚠️ 有条件通 | 单文件 deck-stage 必须先 flatten，否则 5 页里 4 页丢字（校验器会报） |
| deck → PDF（矢量可搜） | ✅ 通 | 5 页 412 KB，文字保留矢量 |
| 动效 → MP4 | ❌ 上游脚本不通 | `render-video.js` 三次都是 `No webm produced`；本仓库给逐帧渲染兜底 |
| 外观账本 / 品味档案（`learn.py` / `ledger`） | ✅ 通 | 写入、按主题回读、范围标注都生效；但 CLI 必填参数比文档多三个 |
| 设计体检（`design_lint check/compare/ledger check`） | ✅ 通 | 裂图、控制台报错、字号、对比度、撞版、模板装饰都能抓 |
| 事实先核实 | ✅ 通（机制有效） | 抓到了「boids 论文 1987 写成 1986」和「凝聚拉满=漩涡」两处错误 |

完整证据（录屏 + 截图 + 原始产物）在 [`report/实测报告.md`](report/实测报告.md)。

---

## 快速开始

```bash
git clone https://github.com/TaurenRen/feifei-design-ops.git
cd feifei-design-ops

# 1. 体检（30 秒，只看不动）
python scripts/doctor.py --skill <你的 huashu-design 目录>

# 2. 缺版本号时补齐（不下载，用目录联接）
python scripts/doctor.py --skill <...> --fix
```

## 四个脚本

| 脚本 | 解决什么 |
|---|---|
| `scripts/doctor.py` | 一次报出六项环境状态；`--fix` 用联接/复制补齐 node 侧要的 chromium、ffmpeg revision |
| `scripts/flatten_deck.py` | 单文件 `<deck-stage>` deck → 所有页同时可见的扁平版，修 PPTX 丢字 |
| `scripts/verify_pptx.py` | 事后复核 PPTX：页数、每页有字文本框、文本 run、和源 HTML 逐页抽样比对丢字 |
| `scripts/render_frames.py` | HTML 动画逐帧渲染成 MP4（确定性，不依赖 Playwright recordVideo） |
| `scripts/rec_harness.py` | 取证录屏：真 cmd 窗口跑真命令 / 真 Chrome 浏览产物，ddagrab 1080p + 运动度验活 |

## 导出 PPTX 的正确顺序

```bash
python scripts/flatten_deck.py deck.html -o deck-flat.html
python <HD>/scripts/pptx_from_rendered.py deck-flat.html -o deck.pptx --selector "section" --bg f6f4ef
python scripts/verify_pptx.py deck.pptx --html deck-flat.html --selector section
```

实测数字：`--selector "deck-stage section"` → 5 个文本框、4 页丢字；flatten 后 → 55 个文本框、0 丢字。

## 动画渲染的正确姿势

```js
window.__step = () => { /* 推进一帧 */ return true; };
window.__setT = (t) => { /* 按第 t 秒设置文字状态 */ return true; };
document.fonts.ready.then(() => requestAnimationFrame(() => { window.__ready = true; }));
```

```bash
python scripts/render_frames.py anim.html --out anim.mp4 --duration 6 --fps 30
```

## 已知限制（写在这里，不是没发现）

- **可编辑 ≠ 1:1 保真**：Google Fonts 里的字体在收件人机器上不存在 → PPTX 里字宽全变、文本框重排。
  要保真给 PDF，要可编辑给 PPTX 并说明是近似版；或把字体装进系统并传 `--font-ea`。
- **可读性底线会否掉微字美学**：HUD 式 11px 等宽标签、杂志式 10px 图注，`design_lint` 一律红灯。
  这是口径不是 bug，抬字号或接受红灯并说明。
- **`compare` 的色板阈值反直觉**：暖纸 `#F4F1EA` vs 灰纸 `#DDD7CC` 距离仅 0.026 判撞版，
  加色块面积也救不回来，最终要靠换材料（牛皮纸）才过 0.146。

## 目录

```
SKILL.md                 给 agent 读的工序层
references/setup.md      安装与版本对齐（含 mklink 命令）
references/pitfalls.md   12 条实测踩坑
scripts/                 doctor / flatten_deck / verify_pptx / render_frames / rec_harness
report/实测报告.md        全量实测记录（含每项的命令、数字、截图索引）
report/recordings/       9 段取证录屏
report/screenshots/      关键截图
```

## 许可

MIT（见 `LICENSE`）。上游 `huashu-design` 为 MIT，版权归其作者；本仓库不包含上游代码，
只在文档中引用其脚本路径与行为。
