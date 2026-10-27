"""Real voice module: per-character monotonic cooldown and loaded spoken taunts."""
from pathlib import Path
import json
from lupa import LuaRuntime

source=Path('outputs/DMC5CharacterSwitch/dmc5_switch_voice.lua').read_text(encoding='utf-8')
names=set(json.loads(Path('work/fixtures/taunt-event-names.json').read_text()))
lua=LuaRuntime()
lua.execute('''
now=0;spoken={};queries=0;fail=false;clockFail=false;randomIndex=0
math.random=function(n)randomIndex=randomIndex+1;return (randomIndex-1)%n+1 end
local function method(name,fn,param)
 return {get_name=function()return name end,
 get_param_types=function()return {{get_full_name=function()return param end}}end,
 call=function(_,...)return fn(...)end}
end
local voice=method('triggerVoice',function(p,event)
 assert(type(event)=='string'and p.container.loaded[event],'unloaded or non-string event')
 assert(event:find('SND_AUTO_PL')==1 and event:find('_V_PROVOCATION_SP_'),'not a spoken taunt')
 if fail then error('native voice failure')end
 spoken[#spoken+1]={id=p.id,event=event,time=now}
end,'System.String')
local exists=method('exists',function(c,event)queries=queries+1;return c.loaded[event]or false end,'System.String')
sdk={typeof=function(n)assert(n=='app.WwiseContainerApp');return n end,
 find_type_definition=function(name)
  if name=='System.Environment'then return {get_method=function(_,n)
   assert(n=='get_TickCount');return {call=function(_,instance)
    assert(instance==nil);if clockFail then error('clock unavailable')end;return now
   end}
  end}end
  return {get_methods=function()
   if name=='app.character.Character'then return {voice}end
   assert(name=='via.wwise.WwiseContainer');return {exists}
  end}
 end}
function actor(id)
 local p={id=id,container={loaded={}}}
 function p:call(n)
  if n=='get_playerID'then return self.id end
  assert(n=='get_GameObject');return {call=function(_,name,t)
   assert(name=='getComponent'and t=='app.WwiseContainerApp');return p.container
  end}
 end
 return p
end
''')
voice=lua.execute(source);lua.globals().V=voice
for actor,code in [(0,'0000'),(1,'0100'),(4,'0800')]:
    pool=list(voice.events[actor].values())
    assert len(pool)>2
    assert all(name in names and name.startswith('SND_AUTO_PL'+code+'_V_PROVOCATION_SP_') for name in pool)
    assert all(name.replace('SND_AUTO_','SND_AUTO_STOP_',1) not in names for name in pool)
lua.execute('''
nero=actor(0);dante=actor(1);vergil=actor(4)
for _,p in ipairs({nero,dante,vergil})do
 for i=1,3 do p.container.loaded[V.events[p.id][i]]=true end
end
assert(V.play(nero));local first=V.lastEvents[0]
now=1;assert(V.play(dante));assert(V.play(vergil))
local count=queries;now=2999;assert(not V.play(nero));assert(queries==count)
-- Actor replacement/floor arrival must not bypass its character's cooldown.
replacement=actor(0);replacement.container=nero.container
assert(not V.play(replacement));assert(#spoken==3)
now=3000;assert(V.play(replacement));assert(V.lastEvents[0]~=first)
assert(not V.play(dante));now=3001;assert(V.play(dante))
local heard={};for i=1,12 do now=now+3000;assert(V.play(nero));heard[V.lastEvents[0]]=true end
local unique=0;for _ in pairs(heard)do unique=unique+1 end;assert(unique==3)
-- Unavailable banks and native failures do not spend a successful-play cooldown.
now=now+3000;nero.container={loaded={}};assert(not V.play(nero))
nero.container.loaded[V.events[0][1]]=true;fail=true;assert(not V.play(nero));assert(V.error)
fail=false;assert(V.play(nero));assert(V.error==nil)
-- A single loaded line remains usable; no blind retry of missing events.
local single=V.lastEvents[0];now=now+3000;assert(V.play(nero));assert(V.lastEvents[0]==single)
now=now+3000;V.enabled=false;assert(not V.play(nero));V.enabled=true;assert(V.play(nero))
assert(not V.play(actor(2))and not V.play(actor(3)))
clockFail=true;now=now+3000;local total=#spoken;assert(not V.play(dante));assert(#spoken==total);clockFail=false
-- Milliseconds cross both signed Int32 transition and full UInt32 wrap.
V.lastPlayed={};now=2147483000;assert(V.play(vergil))
now=-2147483296;assert(not V.play(vergil))
now=-2147481296;assert(V.play(vergil))
V.lastPlayed={};now=-1000;assert(V.play(dante));now=1999;assert(not V.play(dante));now=2000;assert(V.play(dante))
''')
assert 'os.clock' not in source and 'on_frame' not in source and 'sdk.hook' not in source
print('PASS: three native taunt pools, loaded-only random choice, no immediate repeats, independent exact 3000ms cooldown across actors/floors, native failure/clock/disabled handling and signed/full timer wraps; no animation or frame hooks')
