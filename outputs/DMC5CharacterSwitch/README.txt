2026-11-11 keyboard-1：切人键与F10改用独立Windows键态读取，仅游戏前台生效；启动或切回窗口时按住的键须松开后再按。模块失效时停止键盘切人并记录错误，手柄逻辑不变。此项不修复3S与游戏版本不匹配。
2026-11-10 world-v-end-1：切走/切回维吉尔时按需调用原生V模式结束接口，处理召唤与材质收尾；待实机复测。
2026-11-09 presentation-1：切人后结束确属旧角色的特殊镜头；从真魔人切出时清理LDR滤镜。保留现有锁定交接及全部修复。新镜头/滤镜处理待实机验证；未采用全局常态清后处理或清空浮士德帽标记。
2026-11-09：新增锁定目标交接；按住锁定切人时保留同一对象。再次按当前角色的指定键会切回上一个成功切换前的角色，没有历史则忽略；键盘和手柄均适用，重载场景清除历史。
2026-11-09：修复血宫“V的世界”召唤V被当作多余角色停用的问题；按get_ownerVergilPL排除招式召唤物。当前修订 world-v-1，血宫实测招式结束后操作正常。
﻿2026-11-05：手柄快捷键可自定义。启动器分别设置上一位、下一位、尼禄、但丁、维吉尔的副键：A/B/X/Y/LB/LT/RB/RT 或停用。先按住游戏内设置的挑衅键，再按副键；默认上一位 LB、下一位 RB，指定角色组合默认停用。副键不能重复，也不要与当前角色的挑衅键相同。修改后保存，重启游戏生效。
2026-11-05：新增指定角色按键。默认 F7 切到尼禄、F8 切到但丁、F9 切到维吉尔；可在启动器修改或停用。F17/F18 循环切人保留。多个切人键同时按下不切换。旧配置与新增默认键冲突时，仅将冲突的新增键停用。
release-50-native-v-reload
Revision: checkpoint-v-input-audio-2.custom-controls-1.world-v-1.lock-return-1 / 2026-11-09.
Full-party audio loss was traced to the fixed Wwise default pool. The launcher also installs native/audio-pool-fix/winmm.dll to expand that pool to 32 MiB; all 15 Lua modules retain the Dante charge and checkpoint fixes. M3 playback and checkpoint tests passed with zero audio allocation failures.
15 production Lua modules. Build and install with the launcher; see repository README.md.
