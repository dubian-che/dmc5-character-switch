"""Preserve the native enemy-load path when leaving Nero's supply stage."""
from pathlib import Path
from lupa import LuaRuntime
from lua_test_support import install_module_loader

l = LuaRuntime()
install_module_loader(l)
l.execute('''
hooks={};mode=3
sdk={find_type_definition=function(name)return {get_method=function(_,method)return name..'.'..method end}end,
 hook=function(method,pre,post)hooks[method]={pre,post}end,to_managed_object=function(v)return v end}
gm={call=function(_,name)if name=='findManualPlayerID'then return 0 end;assert(name=='get_gameMode');return mode end}
function scenario(id,supply)
 actor={id=id,hp=12345,dt=2345,sin=4567,weapon=6,arms={1,3},call=function(self,name)
  assert(name=='get_playerID','exit repair mutated/read unrelated player state');return self.id
 end}
 manager={call=function(_,name)assert(name=='get_manualPlayer');return actor end}
 bp={CurrentStageNo=4,CurrentFlowState=5,IsGauntletStage=supply,
  CurrentGauntletStageInfo=supply and {}or nil,writes=0,
  get_field=function(self,name)return self[name]end,
  set_field=function(self,name,value)
   assert(name=='IsGauntletStage'or name=='CurrentGauntletStageInfo','repair changed native stage/flow')
   self[name]=value;self.writes=self.writes+1
  end}
 dmc5_switch_loader={manager=manager}
end
sdk.get_managed_singleton=function(name)assert(name=='app.GameManager');return gm end
-- Branches verified in the installed executable's updateCheckGaunletStage:
-- non-Nero jumps to normal floor-init without clearing the supply flag;
-- Nero clears flag + CurrentGauntletStageInfo on an existing supply stage.
function nativeCheck()
 if actor.id==0 and bp.IsGauntletStage then
  bp.IsGauntletStage=false;bp.CurrentGauntletStageInfo=nil
 elseif actor.id==0 and offerSupply then
  bp.IsGauntletStage=true;bp.CurrentGauntletStageInfo={};bp.CurrentFlowState=7;return 'native result'
 end
 bp.CurrentFlowState=6
 return 'native result'
end
''')
l.globals().R = l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_palace.lua').read_text())
l.execute('''
local hook=assert(hooks['app.BloodyPalaceManager.updateCheckGaunletStage'])
for _,id in ipairs({1,4})do
 scenario(id,true)
 -- The unmodified branch keeps presenting empty supply stages.
 nativeCheck();assert(bp.IsGauntletStage and bp.CurrentFlowState==6)
 bp.CurrentFlowState=5
 hook[1]({[2]=bp});assert(hook[2](nativeCheck())=='native result')
 assert(not bp.IsGauntletStage and bp.CurrentGauntletStageInfo==nil)
 assert(bp.CurrentStageNo==4 and bp.CurrentFlowState==6 and bp.writes==2)
 assert(actor.id==id and actor.hp==12345 and actor.dt==2345 and actor.sin==4567 and actor.weapon==6 and actor.arms[1]==1)
 assert(not R.finishGauntletStage(bp,manager,gm)and bp.writes==2,'cleanup repeated after supply flag cleared')
end
-- Nero needs no repair and does not need to pick up an arm for native cleanup.
scenario(0,true);hook[1]({[2]=bp});nativeCheck()
assert(not bp.IsGauntletStage and bp.writes==0 and actor.arms[1]==1)
scenario(0,false);offerSupply=true;hook[1]({[2]=bp});nativeCheck()
assert(bp.IsGauntletStage and bp.CurrentGauntletStageInfo and bp.CurrentFlowState==7 and bp.writes==0)
offerSupply=false
-- Do not remove a newly selected supply stage, touch unrelated actors or modes,
-- or mutate game flow in ordinary battle/training/retry initialization.
for _,id in ipairs({0,1,4,2})do
 scenario(id,false);assert(not R.finishGauntletStage(bp,manager,gm));assert(bp.writes==0)
end
scenario(2,true);assert(not R.finishGauntletStage(bp,manager,gm)and bp.IsGauntletStage)
for _,flag in ipairs({'IsTrainingMode','IsRetryProcessing'})do
 scenario(1,true);bp[flag]=true;assert(not R.finishGauntletStage(bp,manager,gm)and bp.writes==0)
end
scenario(4,true);mode=0;assert(not R.finishGauntletStage(bp,manager,gm)and bp.writes==0)
mode=3;assert(not R.finishGauntletStage(bp,nil,gm));assert(not R.finishGauntletStage(nil,manager,gm))
assert(R.error==nil)
''')
print('PASS: native supply-exit branch repaired only for Dante/Vergil; no pickup required; native flow/stage/enemy loading and player state preserved; Nero, normal battles, retry/training and other modes excluded.')
