import sys
from pathlib import Path
sys.path.insert(0,'work/python-deps')
from lupa import LuaRuntime
from lua_test_support import install_module_loader
l=LuaRuntime()
install_module_loader(l)
l.execute('''
active=0;players={[0]=true};states={[1]=6,[4]=6};calls={};paused=false;scans=0;fps=60
local work={call=function()return 1/fps end}
local hit={get_field=function()return work end}
local actor={call=function(_,name)if name=='get_playerID'then return active else return hit end end}
manager={call=function(_,name,id)
 if name=='get_manualPlayer' then if active>=0 then return actor end
 elseif name=='getPlayerByID' then return players[id] end
end}
local list={call=function(_,name,i)
 if name=='get_Count' then scans=scans+1;return 3 end
 local id=({0,1,4})[i+1]
 return {get_field=function(_,key)if key=='RequestedPlayerID'then return id else return states[id]end end}
end}
loader={get_field=function()return list end,call=function(_,name,id)
 calls[#calls+1]={name,id}
 if name=='requestFinishPlayerResource'then states[id]=7
 elseif name=='requestPreloadPlayerResource'then states[id]=2 end
end}
sdk={hook=function()end,to_managed_object=function(x)return x end,
 find_type_definition=function()return {get_method=function()end}end,
 get_managed_singleton=function(name)if name=='app.GameManager'then return {call=function(_,key)if key=='findManualPlayerID'then return 0 end;return paused end} else return loader end end}
_G.dmc5_live_switch={}
''')
r=l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_lifecycle.lua').read_text())
l.globals().L=r
l.execute('''
function tick(n)for i=1,n do dmc5_switch_runtime.begin();L.update(manager)end end
tick(119);assert(#calls==0)
tick(1);assert(#calls==2 and states[1]==7 and states[4]==7)
assert(scans==8,'loader enumeration still runs every frame')
tick(120);assert(#calls==2)
states[1]=nil;states[4]=nil;tick(15)
assert(#calls==5 and L.repairs==2 and states[0]==2 and states[4]==2)
tick(150);assert(#calls==5)
states[1]=6;players[1]=true
tick(150);assert(#calls==5)
players[1]=nil;paused=true;local oldScans=scans
tick(600);assert(#calls==5 and scans==oldScans,'pause performs scans')
paused=false;active=2
tick(150);assert(#calls==5)
assert(_G.dmc5_live_switch.current==2)
active=0
tick(120);assert(#calls==6)
for _,rate in ipairs({30,75,144})do
 fps=rate;L.missing={};L.recovering={};L.elapsed=0;calls={};scans=0
 states={[1]=6,[4]=6}
 tick(math.floor(fps*1.9));assert(#calls==0,'less than 2 seconds grace')
 tick(math.ceil(fps*.4));assert(#calls==2)
 assert(scans<=10,'too many scans')
end
''')
print('PASS: 30/60/75/144 FPS; >=2 gameplay seconds grace; <=4 scans/sec; async cleanup; pause and scene recovery.')
