"""Manual selection must never replace the native enemy/battle-route identity."""
from mission_control_fixture import make_game
lua=make_game()
lua.execute('''
R.manager=manager
setting.id=-1;manager:call('updateManualPlayer');assert(R.nativeControl==nil)
setting.id=0;active=players[0]
-- Reproduce the old permanent setter: wrong spawn persists after returning Nero.
setting.id=1;local broken=spawn(4);setting.id=0
assert(broken.puppet,'old native battle ownership mismatch not reproduced')
manager:call('updateManualPlayer') -- captures pristine native identity
for _,id in ipairs({1,4,0,4,1})do
 R.selectManual(manager,setting,id)
 assert(active.id==id and setting.id==0)
 assert(not spawn(4).puppet,'Mod selection corrupted native enemy ownership')
 for _=1,1000 do
  manager:call('updateManualPlayer')
  assert(active.id==id and setting.id==0,'native next frame reverted selection or leaked identity')
 end
end
-- Same-setting initialization steal must restore the remembered native ID.
setting.id=4
R.selectManual(manager,setting,0);assert(setting.id==0 and active.id==0)
local ok=pcall(function()R.withControlProfile(setting,4,function()error('native failure')end)end)
assert(not ok and setting.id==0 and R.controlDepth==0)
R.withControlProfile(setting,1,function()
 assert(setting.id==1)
 R.withControlProfile(setting,4,function()assert(setting.id==4)end)
 assert(setting.id==1)
end)
assert(setting.id==0)
-- Native V route remains V. Retry then selects Nero through a new native setting.
nativeID=2;active=players[2];setting=newSetting(2);manager:call('updateManualPlayer')
assert(R.nativeControl.id==2 and not R.prepareStoryRetry(settingManager))
assert(setting.id==2 and not spawn(16).puppet)
nativeID=0;active=players[0];assert(not R.permits(manager),'default Nero asset bypassed selected native V route');active=players[2]
nativeID=0;active=players[0];setting=newSetting(0);manager:call('updateManualPlayer')
assert(R.nativeControl.id==0)
R.selectManual(manager,setting,1);assert(setting.id==0 and not spawn(4).puppet)
assert(R.prepareStoryRetry(settingManager)and setting.id==0)
manager:call('updateManualPlayer');assert(active.id==0 and setting.id==0,'retry retained outgoing selection')
-- New mission/generation must release the old selection to native handoff.
mission=19;nativeID=1;setting=newSetting(1);active=players[1]
dmc5_switch_loader.generation=2;dmc5_switch_loader.storyMission=19
manager:call('updateManualPlayer');R.selectManual(manager,setting,4)
assert(setting.id==1 and active.id==4)
active.event=true;manager:call('updateManualPlayer')
assert(active.id==1 and setting.id==1 and R.controlSelection==nil)
R.selectManual(manager,setting,4);setting.id=2
manager:call('updateManualPlayer');assert(active.id==2 and setting.id==2 and R.controlSelection==nil,'native selection overridden')
assert(R.controlIdentityError==nil,R.controlIdentityError)
''')
print('PASS: old M7 enemy ownership mismatch reproduced; three hero selections and 5000 native refreshes preserve mission identity; nested/failing native calls, initialization steal, V-to-Nero retry, scene/event handoff and native returns covered.')
