import sys
from pathlib import Path
sys.path.insert(0,'work/python-deps')
from lupa import LuaRuntime
from lua_test_support import install_module_loader
l=LuaRuntime()
install_module_loader(l)
l.execute('''
sdk={hook=function()end,find_type_definition=function()return {get_method=function()end}end}
function actor(id,count,stack,hp,enabled,sin,defer)
 local s={count=count,stack=stack,sin=sin,calls=0}
 local p={call=function(_,name,a,b)
  if name=='get_playerID' then return id
  elseif name=='get_hp' then return hp
  elseif name=='get_gauntletNum' then return s.count
  elseif name=='get_gauntletStackCount' then return s.stack
  elseif name=='get_isGauntletPickupEnabled' then return enabled
  elseif name=='pickupGauntlet' then
   assert(a>=0 and a<=7);s.calls=s.calls+1
   if defer then s.stack=1 else s.count=1 end
  elseif name=='get_isTheDevilTrigger' then return s.sin
  elseif name=='get_isDevilTrigger' then return false
  elseif name=='set_devilTriggerBtnOnTimer' or name=='set_devilTriggerPressTimer' then assert(a==0)
  elseif name=='set_isDevilTriggerTimeLineTriggered' then assert(a==false)
  elseif name=='resetDevilTriggerPressCharge' then
  elseif name=='setDevilTrigger' then assert(a==0 and b==true);s.sin=false;s.calls=s.calls+1
  else error(name)end
 end}
 function p:get_field(name)
  assert(name=='IsDoppel'or name=='summonedSwordsControllers');return nil
 end
 return p,s
end
''')
r=l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_resources.lua').read_text())
for defer in (False,True):
 p,s=l.globals().actor(0,0,0,100,True,False,defer)
 assert r.refill(p)
 for _ in range(100): r.refill(p)
 assert s.calls==1
for args in [(0,1,0,100,True,False,False),(0,0,1,100,True,False,False),(0,0,0,0,True,False,False),(0,0,0,100,False,False,False),(1,0,0,100,True,False,False)]:
 p,s=l.globals().actor(*args);assert not r.refill(p);assert s.calls==0
for id,sin in [(1,True),(1,False),(0,False),(4,True),(4,False)]:
 p,s=l.globals().actor(id,1,0,100,True,sin,False)
 expected=id in (1,4) and sin
 assert bool(r.retire(p))==expected
 r.retire(p);assert s.calls==int(expected)
print('PASS: zero stock only, pending pickup, native rejection guard, death, actor scope, repeated ticks and Sin retirement.')
