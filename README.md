# DMC5 Character Switch / 鬼泣 5 三人切换 Mod

[中文](#中文) · [English](#english)

## 中文

Windows 平台的尼禄、但丁、维吉尔实时切换 Mod，使用 REFramework 和游戏原生资源。

**当前版本：1.0.0**。安装包包含适配版 **SSSiyan / 3S 1.24h**、REFramework、声音池修复及中英双语安装器。

[GitHub 下载](https://github.com/dubian-che/dmc5-character-switch/releases/tag/1.0.0) · [Gitee 发行版（国内入口）](https://gitee.com/gutssss/dmc5-character-switch/releases)

两个平台的发行版附件分别维护，仓库同步不会自动上传安装包。请确认下载页列出 **1.0.0** 及 `DMC5-Character-Switch-1.0.0.zip`；若 Gitee 尚未列出，请先使用 GitHub。

### 安装与恢复

1. 从 Release 页面下载 `DMC5-Character-Switch-1.0.0.zip`，完整解压。
2. 完全退出游戏，运行 `DMC5SwitchLauncher.exe`。
3. 点击右上角 **中文 / English** 即时切换语言；未保存的快捷键选择保留。
4. 点击 **安装 / 更新**，选择游戏目录中的 `DevilMayCry5.exe`，完成后从 Steam 启动游戏。

安装器核验游戏程序版本和安装文件，自动备份被覆盖的文件，保留已有切人按键与 3S 设置。版本不匹配时会停止安装。退出游戏后点击 **恢复安装前文件** 可恢复；安装后文件若被改动，恢复会停止以保留修改。

**不要使用旧 C# 启动器覆盖本安装包：其内嵌加载器不是本次已验证版本。**

安装、更新、键盘与手柄快捷键配置、诊断导出、恢复和启动游戏均在同一图形界面内。完整解压并保留 EXE 旁的安装文件，不要只复制 EXE。

### 操作

以下为新安装默认值，已有配置优先。

| 按键 | 功能 |
| --- | --- |
| F5 / F6 | 下一角色 / 上一角色 |
| F7 / F8 / F9 | 尼禄 / 但丁 / 维吉尔 |
| 再按当前角色的指定键 | 返回上一个角色；没有历史则忽略 |
| Delete | 打开 3S 菜单 |
| Insert | 打开 REFramework |
| F10 | 标记诊断现场 |
| 手柄：挑衅 + LB / RB | 上一角色 / 下一角色 |

按住锁定切人时保留同一目标。手柄组合及其他按键见 [安装说明](installer/使用说明.txt)。不要开启 REFramework 的 **Graphics → Hide GUI**，否则游戏菜单会被隐藏。

### 功能与本版修复

- 三人实时切换，原生 HUD 和技能列表随当前角色更新；管理后台角色的输入、显示和碰撞。
- 后台回血与回魔；血宫换层保留角色、资源、武器和机械手状态。
- 修复首次切入但丁时魔剑幻影剑蓄力通道未初始化的问题，无需先切换武器；保留魔剑开刃蓄力。
- 后台角色按游戏选人界面的服装选择加载，修正 EX 服装切场景后恢复默认的问题。
- 32 MiB 声音池修复，处理多角色加载时的间歇缺声。
- 保留“V 的世界”镜头、出招、退场及血宫清层 CG 残留 V 修复。
- 包含 3S 与 REFramework 共存时的启动、画面提交链和菜单修复。

首次幻影剑修复已有实测和 F10 记录验证；服装修复获初步实测确认。67 项自动检查通过，但不能替代实机验收。**并非所有 3S 功能、其他 Mod 组合或游戏版本均已验证。** 曾出现一次 M3 结算闪退，后续未稳定复现，仍需观察。

### 反馈与诊断

异常时按 **F10**，能暂停则暂停。运行 `DMC5SwitchLauncher.exe`，点击 **导出诊断 ZIP** 到桌面；闪退后先导出再重启，避免日志被覆盖。

反馈请注明关卡、角色、3S 开启的功能和最后操作。诊断包含日志、按键配置、角色状态和文件哈希，不包含存档或完整内存转储；日志可能含本机路径与用户名，请检查后再分享。工具不会自动上传。

### 开发与源码

| 路径 | 内容 |
| --- | --- |
| `outputs/DMC5CharacterSwitch/` | 15 个维护中的 Lua 模块，不是构建缓存 |
| `installer/` | 双语安装器、发布清单和说明；不含完整 payload，不能直接安装 |
| `native/` | 声音池修复与独立键盘输入模块 |
| `patches/test-20261114/` | REFramework、3S 补丁、源码基线和第三方许可证 |
| `support/` | F10 状态记录器和说明 |
| `launcher/` | 当前 DesktopLauncher 图形界面、共用配置代码、历史启动器及测试 |
| `scripts/` | 构建、安装和验证脚本 |
| `work/test_*.py` | 离线回归测试 |
| `work/checkpoints/`、`work/reframework-window-fix/` | 旧版本夹具与窗口修复测试材料，不用于当前安装 |

当前图形启动器使用 `scripts/Build-DesktopLauncher.ps1` 构建；`Build-DesktopPackage.ps1 -PayloadPackage <已验证包目录> -OutputDirectory <新目录>` 校验并组装完整安装目录。`Test-DesktopLauncher.ps1 -Launcher <EXE路径>` 应在 Windows PowerShell 5.1 下运行，使用隔离目录验证安装、恢复和设置保存。

历史启动器构建需要 Windows、Windows PowerShell 5.1 和 .NET Framework 4.x C# 编译器：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Launcher.ps1
```

输出为 `dist/DMC5切人启动器/`；`-DiagnosticBuild` 构建历史诊断启动器，`-TestBuild` 启用测试。此流程不重建当前 Release 的全部已验证运行库。原生模块使用 `scripts/Build-AudioPoolFix.ps1` 和 `scripts/Build-KeyboardInput.ps1`，需要 Visual Studio C++ 工具链。

项目历史综合检查入口：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Project.ps1 -Python .\.venv\Scripts\python.exe
```

该入口包含历史启动器构建及验证；当前发布包的安装清单见 `installer/manifest.json`，文件校验值随 Release 提供。

### 来源与许可

- [REFramework](https://github.com/praydog/REFramework)：基于 `d4611aef1d63effd3a736bdf9404ea702428017d`。
- [SSSiyan](https://github.com/youwereeatenbyalid/sssiyan_trainer)：基于 `3aa32ee018048cd8ac01f6acc7c52aca7eb83c36`（1.24h）。

本包使用本地适配版本，并非上游官方二进制；补丁和第三方许可证见 `patches/test-20261114/`。项目自有源码尚未指定开源许可证，第三方代码适用各自许可证。

仓库不包含游戏本体、存档、个人配置、现场诊断记录或崩溃转储；不要求修改游戏 PAK。

[返回顶部](#dmc5-character-switch--鬼泣-5-三人切换-mod) · [English](#english)

---

## English

A Windows mod for switching between Nero, Dante and Vergil in real time, using REFramework and the game's native resources.

**Current release: 1.0.0.** The package includes adapted builds of **SSSiyan / 3S 1.24h** and REFramework, the audio pool fix, and a Chinese/English installer.

[Download on GitHub](https://github.com/dubian-che/dmc5-character-switch/releases/tag/1.0.0) · [Gitee releases (China)](https://gitee.com/gutssss/dmc5-character-switch/releases)

Release assets are maintained separately; mirroring the repository does not upload installers. Check that the page lists **1.0.0** and `DMC5-Character-Switch-1.0.0.zip`. If Gitee does not yet list it, use GitHub.

### Installation and restoration

1. Download `DMC5-Character-Switch-1.0.0.zip` from the Release page and extract the entire archive.
2. Exit the game completely and run `DMC5SwitchLauncher.exe`.
3. Click **中文 / English** in the top-right corner to switch languages instantly. Unsaved binding selections are preserved.
4. Click **Install / Update**, select `DevilMayCry5.exe` in your game folder, then launch the game through Steam.

The installer verifies the game executable and package files, backs up replaced files, and preserves existing character-switch bindings and 3S settings. An unsupported executable stops installation. To restore, exit the game and click **Restore previous files**. Restoration stops if installed files have subsequently changed, preserving those changes.

**Do not overwrite this package with the old C# launcher: its embedded loader is not the version verified for this release.**

Installation, updates, keyboard/controller configuration, diagnostics, restoration and game launch share one desktop UI. Keep the full extracted folder; do not copy the EXE alone.

### Controls

These are defaults for a new installation. Existing settings take priority.

| Key | Action |
| --- | --- |
| F5 / F6 | Next / previous character |
| F7 / F8 / F9 | Nero / Dante / Vergil |
| Press the active character's key again | Return to the previous character; ignored if there is no history |
| Delete | Open the 3S menu |
| Insert | Open REFramework |
| F10 | Mark a diagnostic event |
| Controller: Taunt + LB / RB | Previous / next character |

Holding lock-on while switching preserves the same target. See the [installation guide](installer/README-English.txt) for additional controls. Do not enable **Graphics → Hide GUI** in REFramework, as it hides game menus.

### Features and fixes

- Switch between three characters with native HUD and skill-list updates; manage inactive characters' input, visibility and collision.
- Regenerate inactive characters' health and DT; preserve character selection, resources, weapons and Devil Breakers between Bloody Palace floors.
- Initialize Dante's missing Devil Sword Dante summoned-sword charge channel on first activation, without cycling weapons; preserve the existing sword-expansion charge fix.
- Load reserve characters with costumes selected in the game's character-selection screen, fixing EX costumes reverting after scene changes.
- Expand the audio pool to 32 MiB to address intermittent missing sounds when multiple characters are loaded.
- Preserve World of V camera, execution and cleanup fixes, including the stray V model in Bloody Palace clear cinematics.
- Include startup, presentation-chain and menu fixes for 3S and REFramework coexistence.

The first-activation summoned-sword fix was verified in game and in F10 records; costume preservation has preliminary user confirmation. All 67 automated checks passed, but these do not replace gameplay testing. **Not every 3S feature, other mod combination or game version has been validated.** One M3 results-screen crash has not been consistently reproduced and remains under observation.

### Feedback and diagnostics

When a problem occurs, press **F10** and pause if possible. Run `00-Setup.cmd` and click **Export diagnostics** to export a diagnostic ZIP to Desktop. After a crash, export before restarting to avoid overwriting logs.

Include the mission, character, enabled 3S features and last action in your report. Diagnostics contain logs, bindings, character state and file hashes, but no saves or full memory dumps. Logs may contain local paths and usernames; review them before sharing. Nothing is uploaded automatically.

### Development and source layout

| Path | Contents |
| --- | --- |
| `outputs/DMC5CharacterSwitch/` | 15 maintained Lua modules, not a build cache |
| `installer/` | Bilingual installer, release manifest and guides; incomplete without the release payload |
| `native/` | Audio pool fix and independent keyboard input module |
| `patches/test-20261114/` | REFramework and 3S patches, source baselines and third-party licenses |
| `support/` | F10 state recorder and documentation |
| `launcher/` | Current DesktopLauncher UI, shared settings code, legacy launcher and tests |
| `scripts/` | Build, installation and verification scripts |
| `work/test_*.py` | Offline regression tests |
| `work/checkpoints/`, `work/reframework-window-fix/` | Historical fixtures and window-hook tests, not current installation files |

Build the current GUI with `scripts/Build-DesktopLauncher.ps1`. Use `Build-DesktopPackage.ps1 -PayloadPackage <verified package folder> -OutputDirectory <new folder>` to validate and assemble a complete package. Run `Test-DesktopLauncher.ps1 -Launcher <EXE path>` in Windows PowerShell 5.1 for isolated install, restore and settings tests.

Building the legacy launcher requires Windows, Windows PowerShell 5.1 and a .NET Framework 4.x C# compiler:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Launcher.ps1
```

Output is written to `dist/DMC5切人启动器/`. Use `-DiagnosticBuild` for the legacy diagnostic launcher and `-TestBuild` to enable tests. This workflow does not rebuild every verified runtime in the current release. Native modules use `scripts/Build-AudioPoolFix.ps1` and `scripts/Build-KeyboardInput.ps1`, requiring the Visual Studio C++ toolchain.

The project's legacy comprehensive check entry point is:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Project.ps1 -Python .\.venv\Scripts\python.exe
```

This entry point includes legacy launcher builds and validation. The current package manifest is `installer/manifest.json`; checksums are attached to the Release.

### Sources and licensing

- [REFramework](https://github.com/praydog/REFramework), based on `d4611aef1d63effd3a736bdf9404ea702428017d`.
- [SSSiyan](https://github.com/youwereeatenbyalid/sssiyan_trainer), based on `3aa32ee018048cd8ac01f6acc7c52aca7eb83c36` (1.24h).

The package contains locally adapted builds, not official upstream binaries. Patches and third-party licenses are in `patches/test-20261114/`. No open-source license has yet been assigned to project-owned code; third-party code remains subject to its respective licenses.

The repository excludes the game itself, saves, personal settings, live diagnostic records and crash dumps. Modifying game PAK files is not required.

[中文](#中文) · [Back to English](#english)
