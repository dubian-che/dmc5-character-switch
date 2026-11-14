"""Cover delayed writes after native arrival, outside the reserve Lua task."""
from mission_control_fixture import make_game

lua = make_game()
lua.execute('''
R.manager=manager;R.storyRetrySerial=1
R.storyReloadTail={manager=manager,id=0,mission=7,serial=1,actor=players[0],readyFrames=0,repairs=0}
local B=dmc5_switch_loader
B.count=1;B.playable=true;B.task={id=1}
-- New setting installed AFTER native arrival; no old setting pointer is used.
setting=newSetting(4);R.begin(manager)
assert(setting.id==0 and R.nativeControl.id==0 and not R.storyReload)
R.finish()
-- Main actor stays selectable during tail protection; temporary lookup is scoped.
R.selectManual(manager,setting,1)
assert(active.id==1 and setting.id==0)
for i=1,10 do
 setting.id=4;R.begin(manager);R.finish()
 assert(setting.id==0 and R.storyReloadTail)
end
assert(R.storyTailRepairs==11)
B.task=nil;B.count=3
R.begin(manager);R.finish();assert(R.storyReloadTail)
setting.id=4;R.begin(manager);R.finish()
assert(setting.id==0 and R.storyReloadTail)
R.begin(manager);R.finish();assert(not R.storyReloadTail)
-- The bounded tail is gone; future native handoffs remain native.
setting.id=2;nativeID=2;manager:call('updateManualPlayer')
assert(active.id==2 and R.nativeControl.id==2)
''')
for transition in ("mission=19", "mode=3", "nativeID=1",
                   "R.storyRetrySerial=2", "players[0]={}"):
    lua = make_game()
    lua.execute('''
    R.manager=manager;R.storyRetrySerial=1
    R.storyReloadTail={manager=manager,id=0,mission=7,serial=1,actor=players[0],readyFrames=0,repairs=0}
    ''')
    lua.execute(transition)
    lua.execute('R.maintainStoryReloadTail(manager);assert(not R.storyReloadTail)')
print('PASS: post-arrival replacement settings and off-task writes repaired until two settled native frames; switching remains live; new mission/mode/route/retry/actor boundaries release guard')
