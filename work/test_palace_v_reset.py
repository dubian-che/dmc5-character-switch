from pathlib import Path
from lupa import LuaRuntime
lua=LuaRuntime()
lua.execute('''
hooks={};storage={};mode=3;writes=0
dofile=function()return {}end
thread={get_hook_storage=function()return storage end}
sdk={find_type_definition=function(t)return {get_method=function(_,n)return t..'.'..n end}end,
 hook=function(n,a,b)hooks[n]={a,b}end,to_managed_object=function(v)return v end,
 get_managed_singleton=function()return {call=function()return mode end}end}
med={draw=false,call=function(self,n)assert(n=='get_drawSelf');return self.draw end}
owner={summoned=false,fields={},call=function(self,n)if n=='get_playerID'then return 4 end;assert(n=='get_isSummonGilver');return self.summoned end,
 get_field=function(self,n)return self.fields[n]end}
v={enabled=false,call=function(self,n,arg)
 if n=='get_Enable'then return self.enabled elseif n=='get_ownerVergilPL'then return self.owner
 elseif n=='get_cachedActivateMediator'then return med elseif n=='set_drawSelf'then assert(arg==false);med.draw=arg;writes=writes+1
 else error(n)end end,owner=owner}
owner.fields.summonGilver=v
''')
lua.globals().R=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_resources.lua').read_text())
lua.execute('''
local h=hooks['app.PlayerV.resetStatus'];assert(h and R.worldVResetHook)
for i=1,20 do
 h[1]({[2]=v});med.draw=true;assert(h[2](123)==123);assert(not med.draw)
end
assert(writes==20 and R.worldVResetRepairs==20)
local function excluded()
 h[1]({[2]=v});med.draw=true;assert(h[2](124)==124);assert(med.draw and writes==20);med.draw=false
end
mode=0;excluded();mode=3
owner.summoned=true;excluded();owner.summoned=false
v.enabled=true;excluded();v.enabled=false
owner.fields.IsDoppel=true;excluded();owner.fields.IsDoppel=false
v.owner=nil;excluded();v.owner=owner
owner.fields.summonGilver={};excluded();owner.fields.summonGilver=v
med.draw=true;excluded()
-- If native reset activates the skill, do not undo that transition.
h[1]({[2]=v});owner.summoned=true;med.draw=true;h[2](0);assert(med.draw and writes==20)
owner.summoned=false;med.draw=false
-- Distinct hook storage survives nested callbacks, just as RF provides it.
local outer=storage;h[1]({[2]=v});storage={};h[1]({[2]=v});med.draw=true;h[2](0)
storage=outer;med.draw=true;h[2](0);assert(not med.draw and writes==22)
assert(not R.worldVResetError)
''')
print('PASS: native redisplay corrected; return preserved; active summon, visible V, story, foreign/clone and nested callback guards')
