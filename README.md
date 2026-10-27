# DMC5 Character Switch / 鬼泣 5 三人切换 Mod

Windows 平台的尼禄、但丁、维吉尔实时切换 Mod，使用 REFramework 和游戏原生资源。
公开版本：**pre-0.0.1（预发布）**。

[GitHub 下载安装包](https://github.com/dubian-che/dmc5-character-switch/releases/tag/pre-0.0.1) · [Gitee 发行版](https://gitee.com/gutssss/dmc5-character-switch/releases)

两个平台的发行版附件分别维护，请按对应发行版页面实际列出的附件下载。

当前源码基线：**release-47-scripted-movement-guard**；可选诊断启动器：**support-47.1**。

## 功能

- 三人切换、原生 HUD 和技能列表跟随当前角色；启动器可配置切换按键。
- 保留切换位置，管理后台角色的显示、输入和世界碰撞。
- 后台角色每两秒回复一格血，保留后台回魔。
- 血宫换层保存当前角色及资源、武器和机械手状态。
- 切入角色随机播放已加载的挑衅语音，同角色三秒冷却。
- 原生 V 关卡走隔离流程，不加入三人切换。

本仓库不包含游戏文件、存档、个人配置、现场诊断记录或崩溃转储。
REFramework 的 MIT 运行库及用于回归测试的旧运行库随源码提供，许可证见对应依赖目录。

## 构建

需要 Windows、Windows PowerShell 5.1 和 .NET Framework 4.x C# 编译器。
在仓库根目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Launcher.ps1
```

输出在 `dist/DMC5切人启动器/`。运行启动器并选择游戏目录，关闭游戏后安装或更新。
安装器维护文件归属和备份记录；已有未知加载器时需先处理冲突。
本仓库不分发游戏本体，也不要求修改游戏 PAK。

## 可选远端诊断版

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Launcher.ps1 -DiagnosticBuild
```

输出在 `dist/DMC5远端诊断启动器/`。该版本可安装只读记录器，导出最近 30 分钟的诊断 ZIP 到桌面。
记录从启用并重启游戏后开始，不会补录此前历史。支持 F8 现场标记、问题描述及可选的游戏截图。
导出包可能包含游戏日志、相关系统错误和崩溃信息，请按实际需要提供给维护者。
正式构建不包含该记录器。详情见 [诊断版使用说明](support/使用说明.txt)。

## 离线检查

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Test-Project.ps1 -Python .\.venv\Scripts\python.exe
```

模拟测试与安装器测试不启动游戏，不能替代实机验收。诊断启动器另有条件编译测试：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Build-Launcher.ps1 -DiagnosticBuild -TestBuild
```

## 源码结构

| 路径 | 内容 |
| --- | --- |
| `outputs/DMC5CharacterSwitch` | 15 个正式 Lua 模块；这是维护源码，不是构建缓存 |
| `launcher` | C# 启动器、安装器、条件编译测试和诊断导出器 |
| `scripts` | 构建、安装及发布验证脚本 |
| `support` | 可选只读记录器和说明 |
| `work/test_*.py` | 离线回归测试 |
| `work/checkpoints` | 测试实际引用的旧源码/运行库夹具，不用于安装 |
| `work/reframework-window-fix` | REFramework 窗口消息链修补、原始/修改源码及 Win32 回归测试 |

## 依赖与范围

REFramework 上游：[praydog/REFramework](https://github.com/praydog/REFramework)，基于提交
`d4611aef1d63effd3a736bdf9404ea702428017d` 做本地窗口消息链修补。
固定 DLL 的 SHA-256：`CBA7C25F57D199E2FDFB73EB3BA8BA5BAF028D453D428498796E85FBDD75CB0F`。
这不是上游官方二进制；补丁及许可证随仓库提供。

本 Mod 面向特定 DMC5/REFramework 环境，其他 Mod、游戏版本与关卡流程仍需实测。
声音间歇缺失、个别原生崩溃的原因尚未完全确认；幻影剑特效可能在切换后残留。
未为项目自有源码指定开源许可证；第三方代码适用各自许可证。
