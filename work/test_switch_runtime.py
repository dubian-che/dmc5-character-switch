import sys
from pathlib import Path
sys.path.insert(0, 'work/python-deps')
from lupa import LuaRuntime

l = LuaRuntime()
l.execute('''
reads=0;activeID=0;paused=false;deltaReads=0;singletonReads=0
local work={call=function()deltaReads=deltaReads+1;return 1/60 end}
local hit={get_field=function()return work end}
local player={call=function(_,name)if name=='get_playerID'then return activeID else return hit end end}
manager={call=function()reads=reads+1;return player end}
sdk={to_managed_object=function(x)return x end,hook=function(_,pre,post)begin=pre;finish=post end,find_type_definition=function()return {get_method=function()end}end,
 get_managed_singleton=function()singletonReads=singletonReads+1;return {call=function()return paused end}end}
''')
l.globals().R = l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_runtime.lua').read_text())
l.execute('local nativeBegin=begin;begin=function()nativeBegin({[2]=manager})end')
l.execute('''
for frame=1,60 do
 begin()
 for module=1,5 do local c=R.get(manager);assert(c.id==0);assert(R.delta(c)==1/60)end
end
assert(reads==60 and singletonReads==60 and deltaReads==60,'state not shared across consumers')
activeID=1;R.invalidate();assert(R.get(manager).id==1,'handoff reused stale player')
paused=true;begin();assert(R.delta(R.get(manager))==0)
assert(R.run==nil and R.metrics==nil and R.profiling==nil,'development sampler shipped')
os.clock=function()error('performance clock must not run in release')end
paused=false
for i=1,600 do begin();assert(R.delta(R.get(manager))==1/60)end
local completed=0
begin()
R.afterUpdate(function()completed=completed+1 end)
assert(completed==0,'placement ran before native update')
assert(finish(123)==123 and completed==1,'native result or completion was lost')
finish(123);assert(completed==1,'placement repeated across frames')
begin()
R.afterUpdate(function()error('placement error')end)
R.afterUpdate(function()completed=completed+1 end)
finish(456)
assert(completed==2 and R.error:find('placement error'),'completion errors were not isolated')
R.afterUpdate(function()completed=completed+1 end)
assert(completed==3,'standalone invocation lost its completion')
''')
print('PASS: shared cache, pause exclusion, one-shot completion after native update, return preservation and isolated completion errors; no release sampler.')
