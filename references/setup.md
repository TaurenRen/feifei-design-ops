# 安装与版本对齐

## 1. 拿源码

```bash
# 直连 clone 在本机不通（curl 28），用 codeload
curl -L -o huashu.tar.gz https://codeload.github.com/alchaincyf/huashu-design/tar.gz/refs/heads/master
mkdir -p ~/.workbuddy/skills/huashu-design
tar -xzf huashu.tar.gz -C ~/.workbuddy/skills/huashu-design --strip-components=1
```

上游也支持 `npx skills add alchaincyf/huashu-design`（走 npm + git，本机网络未验证）。

## 2. python 依赖

```bash
pip install playwright pillow python-pptx
python -m playwright install chromium
```

- `playwright` + `chromium`：`design_lint.py`、`ref_board.py`、`pptx_from_rendered.py`、`verify.py` 都要
- `pillow`：`ref_board.py` 的「几乎纯色」判定、`design_lint.py` 的截图分析
- `python-pptx`：PPTX 导出与复核

## 3. node 依赖

```bash
cd ~/.workbuddy/skills/huashu-design
npm install                                   # pdf-lib / playwright / pptxgenjs / sharp
npx playwright install chromium ffmpeg        # 注意：这是 node 侧自己的浏览器与 ffmpeg
```

**不要以为 python 侧装过就够了。** 两边要的 revision 不同（实测 python=chromium-1248 / ffmpeg-1013，
node=chromium-1217 / ffmpeg-1011）。若下载被限速，用 `doctor.py --fix` 做目录联接：

```
mklink /J %LOCALAPPDATA%\ms-playwright\chromium-1217 %LOCALAPPDATA%\ms-playwright\chromium-1248
mklink /J %LOCALAPPDATA%\ms-playwright\chromium_headless_shell-1217 %LOCALAPPDATA%\ms-playwright\chromium_headless_shell-1248
copy %LOCALAPPDATA%\ms-playwright\ffmpeg-1013\ffmpeg-win64.exe %LOCALAPPDATA%\ms-playwright\ffmpeg-1011\
```

联接前把目标版本号看清楚：报错信息里那个 `...\chromium-XXXX\chrome-win64\chrome.exe` 就是 node 侧要的。

## 4. 在项目目录里用上游脚本（ESM 找不到模块时）

上游 `scripts/*.mjs` 是 ESM，`NODE_PATH` 对它无效。要么把脚本放到 skill 目录里跑，
要么在项目目录建一个指向 skill `node_modules` 的联接：

```
mklink /J 项目目录\node_modules %USERPROFILE%\.workbuddy\skills\huashu-design\node_modules
```

## 5. ffmpeg

`render_frames.py` 默认写死本机路径 `D:\ProgramData\ffmpeg-win64\bin\ffmpeg.exe`；
换机器改文件头常量，或把 ffmpeg 放进 PATH（脚本会先试 PATH）。

## 6. 验证

```bash
python scripts/doctor.py --skill ~/.workbuddy/skills/huashu-design
```

六项全 OK 再开始做设计，否则后面每一步导出都会以「playwright 报错」的面目出现。
