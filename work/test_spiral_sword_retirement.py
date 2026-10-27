"""Exercise real retirement cleanup; unrelated actors and sword patterns survive."""
from pathlib import Path
from lupa import LuaRuntime

lua = LuaRuntime()
lua.execute('''
sdk={hook=function()end,find_type_definition=function()return {get_method=function()return {}end}end}
dofile=function()return {}end
events={}
function actor(id,clone)
 local p={id=id,clone=clone,dt=6000,sin=7000,controllers={}}
 function p:get_field(n)
  if n=='IsDoppel'then return self.clone end
  assert(n=='summonedSwordsControllers')
  return {call=function(_,method,i)
   if method=='get_Count'then return #self.controllers end
   assert(method=='get_Item');return self.controllers[i+1]
  end}
 end
 function p:call(n,...)
  if n=='get_playerID'then return self.id end
  if n=='get_isDevilTrigger'or n=='get_isTheDevilTrigger'then return false end
  assert(n=='set_devilTriggerBtnOnTimer'or n=='set_devilTriggerPressTimer'or
   n=='resetDevilTriggerPressCharge'or n=='set_isDevilTriggerTimeLineTriggered')
  events[#events+1]='human'
 end
 return p
end
function sword(owner,kind,ended,mutate)
 local c={owner=owner,ended=ended,cancels=0,shells=6}
 function c:get_type_definition()return {get_name=function()return kind end}end
 function c:call(n)
  if n=='get_owner'then return self.owner end
  if n=='get_isEnd'then return self.ended end
  assert(n=='cancel');assert(not self.ended)
  self.cancels=self.cancels+1;self.shells=0;self.ended=true
  events[#events+1]='cancel'
  if mutate then table.remove(owner.controllers,1)end
 end
 owner.controllers[#owner.controllers+1]=c
 return c
end
''')
lua.globals().resources = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_resources.lua').read_text(encoding='utf-8'))
lua.execute('''
p=actor(4);foreign=actor(4)
a=sword(p,'SpiralSwordsController',false,true)
b=sword(p,'SpiralSwordsController',false,false)
other=sword(p,'StormSwordsController',false,false)
finished=sword(p,'SpiralSwordsController',true,false)
alien=sword(p,'SpiralSwordsController',false,false);alien.owner=foreign
resources.retire(p)
assert(a.cancels==1 and b.cancels==1 and a.shells==0 and b.shells==0)
assert(events[1]=='cancel'and events[2]=='cancel'and events[3]=='human')
assert(other.cancels==0 and finished.cancels==0 and alien.cancels==0)
assert(p.dt==6000 and p.sin==7000)
assert(resources.dismissSpiralSwords(p)==0 and b.cancels==1)
for _,id in ipairs({0,1,2,3})do
 local q=actor(id);local c=sword(q,'SpiralSwordsController',false,false)
 assert(resources.dismissSpiralSwords(q)==0 and c.cancels==0)
end
q=actor(4,true);c=sword(q,'SpiralSwordsController',false,false)
assert(resources.dismissSpiralSwords(q)==0 and c.cancels==0)
assert(resources.dismissSpiralSwords(actor(4))==0)
-- Do not park an actor after an unconfirmed native cancellation.
bad=actor(4);c=sword(bad,'SpiralSwordsController',false,false)
c.call=function(self,n)
 if n=='get_owner'then return bad end
 if n=='get_isEnd'then return false end
 assert(n=='cancel')
end
events={};assert(not pcall(resources.retire,bad));assert(#events==0)
''')
core = Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text(encoding='utf-8')
assert core.index('resources.retire(previous)') < core.index('parkWorldCollision(previous)', core.index('resources.retire(previous)'))
print('PASS: native Spiral Swords retirement, owner/type isolation, mutation-safe snapshot, idempotence and failure containment')
