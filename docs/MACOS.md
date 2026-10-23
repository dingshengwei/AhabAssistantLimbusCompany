# AALC for macOS（macOS 分支）

上游项目：[KIYI671/AhabAssistantLimbusCompany](https://github.com/KIYI671/AhabAssistantLimbusCompany)（AGPL-3.0）。
本分支在保留上游业务代码的前提下，增加了一层 macOS 平台适配，让 AALC 能在 Apple Silicon
Mac 上从源码运行。

> 说明：上游 Release 只有 Windows(x86_64) 版本，官方 README 明确写到暂不支持 Mac/Linux。
> 本分支的上游基线 commit 见仓库首个提交的说明。

![AALC 在 macOS 上运行](images/aalc-macos-gui.png)

## 仓库与分支

| 项 | 值 |
|---|---|
| 上游 | [KIYI671/AhabAssistantLimbusCompany](https://github.com/KIYI671/AhabAssistantLimbusCompany) |
| 本分支 | [dingshengwei/AhabAssistantLimbusCompany `macos`](https://github.com/dingshengwei/AhabAssistantLimbusCompany/tree/macos)（已推送） |
| 基线 | 上游 `main` @ `e1d1749`（2026-10-19） |
| 本地目录 | `~/workspace/dshspace/AALC` |
| 开 PR | https://github.com/dingshengwei/AhabAssistantLimbusCompany/pull/new/macos |

与上游保持同步：

```bash
cd ~/workspace/dshspace/AALC
git fetch upstream
git merge upstream/main      # 冲突优先保留 module/platform 与 IS_MACOS 分支
git push origin macos
```

## 免费的游戏运行方式

MuMu Pro 是收费的，macOS 上可以完全免费跑起来，按推荐顺序：

| 方案 | 费用 | AALC 走哪条链路 | 适配度 |
|---|---|---|---|
| **PlayCover**（本机已装） | 免费开源 | 原生窗口（ScreenCaptureKit + CGEvent） | 实验性：需把窗口设成 16:9 |
| **BlueStacks Air** | 免费（可选购会员） | adb（`simulator_type=10`，端口 5555） | 好，安卓版 16:9 |
| **Android Studio AVD** | 完全免费开源 | adb（端口 5555） | 好，但性能一般、内存占用高 |
| ~~MuMu Pro~~ | 收费 | adb（端口 16384） | 好，但要花钱 |

**结论**：想零成本又稳，选 **BlueStacks Air**（安卓版 + adb）；不想再装模拟器就用 **PlayCover**，但必须把窗口调成 16:9，否则模板会错位。

### PlayCover 方式（零安装成本）

1. PlayCover 里安装并启动 Limbus Company；
2. 打开 PlayCover 的「应用设置 → 显示」：
   - 窗口尺寸填 **1920 × 1080**（或用自定义分辨率），宽高比选 **16:9**
   - 关掉「悬浮窗 / 隐藏标题栏」之类会改变窗口尺寸的选项
3. AALC 设置里**不要**勾选「使用模拟器」，键鼠保持「前台」；
4. 首次运行 AALC 会通过 `CGWindowList` 找到窗口，并自动把本次会话的分辨率基准
   对齐到窗口高度（`cfg.set_win_size`，只改内存不落盘）。

> PlayCover 默认是 iPad 的 4:3 画布，AALC 的模板全部按 16:9 制作。窗口不是 16:9 时
> AALC 会在日志里告警并大概率识别失败，务必先按上面的方式改成 1920×1080。
> 若画面上下/左右出现黑边（应用内 letterbox），也需要在应用设置里改成拉伸/填充。

### BlueStacks Air / Android Studio AVD（安卓版 + adb）

1. 安装 [BlueStacks Air](https://www.bluestacks.com/mac)（Apple Silicon 版，免费）
   或 Android Studio 的 AVD（Android 11+ arm64 镜像）；
2. 打开 ADB 调试：
   - BlueStacks Air：设置 → 高级 → 开启 Android Debug Bridge（默认 `127.0.0.1:5555`）
   - AVD：启动时加 `-writable-system` 即可，adb 端口固定 `5555`
3. 装好 adb（本仓库脚本，一次性）：

   ```bash
   ./scripts/setup_adb_macos.sh          # 下载官方 platform-tools 到 assets/binary/platform-tools
   ```

4. AALC 设置页：勾选「使用模拟器」→ 类型选「其他」→ 主机 `127.0.0.1` → 端口 `5555`
5. 游戏分辨率建议在模拟器里设成 **1920×1080（16:9）**，与 `set_win_size` 一致。

`config.yaml` 对应键：

```yaml
simulator: true
simulator_type: 10
simulator_host: 127.0.0.1
simulator_port: 5555     # MuMu Pro 用户填 16384
```

> 注：AALC 启动时会按 PATH、`assets/binary/platform-tools`、`~/Library/Android/sdk`
> 的顺序找 adb；找不到会在日志里提示运行 `scripts/setup_adb_macos.sh`。

## 安装与启动

前置：Python 3.12+（`brew install python@3.12`）、Xcode Command Line Tools。

```bash
cd AALC
./scripts/run_macos.sh        # 首次会建 .venv 并安装 requirements-macos.txt
```

也可以手动：

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-macos.txt
.venv/bin/python main.py
```

首次启动需要在 AALC 里完成两项授权（系统设置 → 隐私与安全性）：

1. **屏幕录制**：截图用。未授权时截图会全黑/失败。
2. **辅助功能**：点击、拖拽、按键用。未授权时操作会被系统静默丢弃。

授权对象是「运行 AALC 的终端 / Python」或打包后的 `AALC.app`；改完权限需重启进程。

## 使用 PlayCover（实验性）

1. 用 PlayCover 安装并启动 Limbus Company，把窗口放在主屏、不要最小化。
2. AALC 设置页关闭「使用模拟器」，「键鼠操控方式」保持「前台」。
3. 首次运行 AALC 会尝试通过 `CGWindowList` 找到名为 `LimbusCompany` 的窗口。

已知限制：

- macOS 无法像 Win32 那样向非前台窗口投递消息，所以「后台点击」在 Mac 上等于前台点击。
- 窗口置顶/去边框/固定分辨率等 Win32 窗口样式操作在 macOS 上无效，
  「自动设置窗口」默认关闭。
- PlayCover 窗口是 iPad 比例，模板匹配容易偏，需要按实际分辨率重新校准图片资源。

## 已实现 / 未实现

已实现：

- `module.platform.macos`：窗口枚举与几何（Quartz）、窗口激活/移动/缩放（Accessibility）、
  窗口截图（ScreenCaptureKit，失败回退 `screencapture`）、鼠标键盘输入（CGEvent）、系统通知（osascript）。
- `module.platform.win32_compat`：在 macOS 上注入 `win32gui / win32con / win32api / win32ui /
  win32process / winreg / pywintypes / pyuac / win32crypt / win32com.client` 替身，
  上游业务代码不需要改 import。
- `main.py`：跳过 UAC 提权与 DPI 设置，安装兼容层并按平台调整默认配置。
- macOS 输入后端 `MacInput`（复用 pyautogui/CGEvent，中文输入走剪贴板 + Cmd+V）。
- 游戏启动：`open -a`（PlayCover / BlueStacks Air / MuMu Pro）。
- 通知：macOS 通知中心。

未实现 / 待办：

- PyInstaller `.app` / dmg 打包与签名、公证（下一步）。
- 自动更新：macOS 上直接跳过（上游更新包是 Windows exe/7z）。
- 关机/休眠/锁屏、开机自启、任务计划等 Windows 专属功能。
- 模拟器的“一键启动/多开管理”（上游依赖 Windows 注册表与 MuMuManager.exe；BlueStacks Air / AVD 需手动启动）。
- 性能：当前每次截图重新创建 ScreenCaptureKit 会话（约 200 ms），后续可复用 `SCStream` 降到 10 ms 级。

## 目录结构（新增部分）

```
module/platform/
├── __init__.py            # IS_MACOS / IS_WINDOWS 等平台标志
├── macos/
│   ├── display.py         # 显示器信息、Retina 缩放、Win32 坐标换算
│   ├── window.py          # CGWindowList / AX：查找、几何、激活、移动
│   ├── capture.py         # ScreenCaptureKit 截图（+ screencapture 回退）
│   ├── input.py           # MacInput：CGEvent 点击/拖拽/滚动/按键
│   ├── notify.py          # osascript 通知
│   └── bootstrap.py       # 兼容层安装、权限检查、macOS 默认配置
└── win32_compat/          # win32* 模块替身（只在 darwin 上注入）
```

## 与上游同步

```bash
git remote add upstream git@github.com:KIYI671/AhabAssistantLimbusCompany.git  # 已配置
git fetch upstream
git merge upstream/main     # 解决冲突时优先保留 module/platform 与 IS_MACOS 分支
```

移植改动尽量收敛在 `module/platform/`、`main.py` 少量平台分支、以及
`screenshot.py / automation.py / game.py / utils.py / check_update.py / windows_toast.py / hdr.py`
里的 `IS_MACOS` 判断，便于跟随上游合并。

## 许可

上游为 AGPL-3.0，本分支同样遵循 AGPL-3.0，分发时需保留版权与许可声明。
