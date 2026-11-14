$Messages=@{
 Title=@('DMC5 切人 + 3S 测试包','DMC5 Character Switch + 3S Test Package')
 Install=@('安装 / 更新','Install / Update')
 Collect=@('导出诊断到桌面','Export diagnostics to Desktop')
 Restore=@('恢复安装前的文件','Restore previous files')
 Quit=@('退出','Exit')
 Hint=@('直接按数字操作，无需回车。按 L 立即切换语言。','Press a number without Enter. Press L to switch language instantly.')
 Pick=@('请选择游戏目录中的 DevilMayCry5.exe','Select DevilMayCry5.exe in the game folder')
 Folder=@('请选择包含 DevilMayCry5.exe 的游戏目录。','Select the game folder containing DevilMayCry5.exe.')
 Path=@('安装包路径无效。','Invalid package path.')
 Exported=@('诊断包已保存：{0}','Diagnostics saved: {0}')
 Running=@('请先完全退出鬼泣5，再安装或恢复。','Exit Devil May Cry 5 completely before installing or restoring.')
 NoBackup=@('未找到此测试包的安装备份。','No backup from this test package exists.')
 BackupPath=@('备份路径无效。','Invalid backup path.')
 Changed=@('文件在安装后已被修改，为保留修改已停止恢复：{0}','File changed since installation; restore stopped to preserve it: {0}')
 Restored=@('已恢复原文件，备份仍保留。','Previous files restored. Backup retained.')
 Version=@('游戏程序与本包实测版本不一致，已停止安装，未修改游戏文件。请将游戏版本信息反馈给制作者，不要删除版本校验。','This game executable differs from the tested version. Nothing installed. Report your game version to the package author; do not remove the version check.')
 Integrity=@('安装包文件校验失败，请重新解压完整压缩包：{0}','Package integrity check failed. Extract the complete archive again: {0}')
 Hash=@('安装后的文件校验失败：{0}','Installed file hash mismatch: {0}')
 Installed=@('安装完成。请从 Steam 启动；Delete 打开 3S，F10 记录诊断。','Installed. Start from Steam. Delete opens 3S; F10 records diagnostics.')
 Backup=@('备份位置：{0}','Backup: {0}')
 Error=@('操作未完成。请检查目录权限、文件是否被占用以及安装包完整性。详细信息：','Operation failed. Check folder permissions, files in use and package integrity. Details:')
 Back=@('按任意键返回；也可按 L 切换语言并查看本次结果。','Press any key to return, or L to switch language and view this result.')
 Working=@('正在执行，请稍候……','Working, please wait...')
 Cancelled=@('已取消选择，未执行操作。','Selection cancelled; no operation performed.')
 NotSaved=@('本目录无法保存语言偏好，本次切换仍然有效。','Language preference could not be saved here; the current selection still applies.')
}
function T([string]$Key,[object[]]$Values=@()){
 $index=if($script:Language -eq 'en'){1}else{0}
 $text=$Messages[$Key][$index]
 if($Values.Count){return $text -f $Values};return $text
}
