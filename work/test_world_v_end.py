from pathlib import Path
from lupa import LuaRuntime
l=LuaRuntime();l.execute('dofile=function()return {}end;sdk={hook=function()end,find_type_definition=function()return {get_method=function()end}end}')
l.globals().R=l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_resources.lua').read_text())
l.execute('''
count=0;id=4;clone=false;summoned=false;material=false;visible=false
v={call=function(_,n)if n=='get_ownerVergilPL'then return foreign and {} or p end assert(n=='get_Enable');return visible end}
p={get_field=function(_,n)if n=='IsDoppel'then return clone elseif n=='isChangeMaterialVmode'then return material elseif n=='summonGilver'then return v end error(n)end,
call=function(_,n,a,b,c)if n=='get_playerID'then return id elseif n=='get_isSummonGilver'then return summoned elseif n=='vModeEnd'then assert(a==false and b==true and c==true);count=count+1;if failure then error('native failure')end;summoned=false;material=false;visible=false;return end error(n)end}
assert(not R.finishWorldV(p) and count==0)
for _,pid in ipairs({0,1,2})do id=pid;material=true;assert(not R.finishWorldV(p))end
id=4;clone=true;assert(not R.finishWorldV(p));clone=false
assert(R.finishWorldV(p) and count==1)
summoned=true;assert(R.finishWorldV(p) and count==2)
visible=true;assert(R.finishWorldV(p) and count==3)
assert(not R.finishWorldV(p) and count==3)
visible=true;foreign=true;assert(not R.finishWorldV(p));foreign=false
failure=true;assert(not pcall(R.finishWorldV,p))
''')
s=Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text();assert s.index('resources.finishWorldV(target)')<s.index('M.resetEntryAction(target,airborne)',s.index('resources.finishWorldV(target)'))
print('PASS: native V exit for active/stale summon and material; normal actors/clones untouched; no warp; failures propagate; cleanup precedes reset.')
