from pathlib import Path
from lupa import LuaRuntime
l=LuaRuntime()
l.execute('''
hooks={};threadID=1;stacks={}
thread={get_id=function()return threadID end,get_hook_storage=function()local s=stacks[threadID];return s and s[#s]end}
dofile=function()return {permits=function()return allowed~=false end}end
sdk={find_type_definition=function(t)return {get_method=function(_,n)return t..'.'..n end}end,
hook=function(m,a,b)hooks[m]={function(args)stacks[threadID]=stacks[threadID]or{};table.insert(stacks[threadID],{});return a(args)end,
function(ret)local result=b(ret);table.remove(stacks[threadID]);return result end}end,to_managed_object=function(v)return v end,
to_int64=function(v)return v end,to_ptr=function(v)return v end,
get_managed_singleton=function(n)assert(n=='app.PlayerManager');return manager end}
camera={};foreignCamera={};foreignV={};clone=false;summoned=true;ownerID=4
owner={get_field=function(_,n)if n=='IsDoppel'then return clone end assert(n=='summonGilver');return summon end,
call=function(_,n)if n=='get_playerID'then return ownerID elseif n=='get_camera'then return camera elseif n=='get_isSummonGilver'then return summoned end error(n)end}
summon={call=function(_,n)if n=='get_playerID'then return 2 end assert(n=='get_ownerVergilPL');return wrongOwner and foreignV or owner end}
manager={call=function(_,n)assert(n=='get_manualPlayer');if fail then error('stale owner')end;return owner end}
''')
l.globals().R=l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_resources.lua').read_text())
l.execute('''
assert(R.worldVCameraHooked and not R.worldVCameraError)
follow=hooks['app.PlayerCameraController.FollowCameraV(System.Boolean)']
lookup=hooks['app.PlayerManager.getPlayerByID(app.PlayerID)']
late=hooks['app.PlayerCameraController.lateUpdate']
function query(id,m)lookup[1]({[2]=m or manager,[3]=id});return lookup[2](foreignV)end
assert(query(2)==foreignV)
follow[1]({[2]=camera});assert(query(2)==summon and query(0)==foreignV and query(2,{})==foreignV)
lookup[1]({[2]=manager,[3]=2});lookup[1]({[2]=manager,[3]=0})
assert(lookup[2](foreignV)==foreignV and lookup[2](foreignV)==summon)
threadID=2;assert(query(2)==foreignV);threadID=1
follow[1]({[2]=foreignCamera});assert(query(2)==foreignV);assert(follow[2](456)==456)
assert(query(2)==summon);assert(follow[2](123)==123);assert(query(2)==foreignV)
-- Native lateUpdate has its own ID-2 lookup and does not call FollowCameraV.
for i=1,120 do
 late[1]({[2]=camera});assert(query(2)==summon and query(4)==foreignV)
 follow[1]({[2]=camera});assert(query(2)==summon);follow[2](0)
 assert(query(2)==summon);late[2](0);assert(query(2)==foreignV)
end
for _,case in ipairs({'clone','summoned','ownerID','wrongOwner','fail'})do
 clone=case=='clone';summoned=case~='summoned';ownerID=case=='ownerID'and 0 or 4;wrongOwner=case=='wrongOwner';fail=case=='fail'
 follow[1]({[2]=camera});assert(query(2)==foreignV);follow[2](0);assert(query(2)==foreignV)
end
assert(#stacks[1]==0 and #stacks[2]==0)
clone=false;summoned=true;ownerID=4;wrongOwner=false;fail=false
local originalCall=summon.call
summon.call=function(self,n)if n=='get_Enable'then return enabled~=false end return originalCall(self,n)end
foreignV.call=function(_,n)assert(n=='get_playerID');return targetID or 2 end
local target=foreignV;local writes=0
local accessor={get_type_definition=function()return {get_full_name=function()return accessorType or 'app.PlayerAccessor'end}end,
call=function(_,n,v)if n=='get_player'then return target end assert(n=='set_player');writes=writes+1;target=v end}
camera.get_field=function(_,n)assert(n=='FollowCameraPlayer');return followID or 2 end
camera.call=function(_,n)assert(n=='get_player');return accessor end
assert(R.repairWorldVCamera(camera,manager));assert(target==summon and writes==1)
assert(not R.repairWorldVCamera(camera,manager));assert(writes==1)
for _,case in ipairs({'scene','inactive','clone','owner','disabled','camera','accessor','target'})do
 target=foreignV;allowed=case~='scene';summoned=case~='inactive';clone=case=='clone';wrongOwner=case=='owner'
 enabled=case~='disabled';followID=case=='camera'and 4 or 2;accessorType=case=='accessor'and 'app.OtherAccessor'or 'app.PlayerAccessor';targetID=case=='target'and 0 or 2
 assert(not R.repairWorldVCamera(camera,manager));assert(writes==1)
end
allowed=true;summoned=true;clone=false;wrongOwner=false;enabled=true;followID=2;accessorType='app.PlayerAccessor';targetID=2
-- A later native overwrite must be repaired again, without a one-shot cache.
assert(R.repairWorldVCamera(camera,manager));assert(writes==2 and target==summon)
local treeEnabled=false;local treeWrites=0
local tree={call=function(_,n,v)if n=='get_Enabled'then return treeEnabled end assert(n=='set_Enabled'and v==true);treeEnabled=v;treeWrites=treeWrites+1 end}
local summonCall=summon.call
summon.call=function(self,n)if n=='get_cachedBehaviorTree'then return tree end return summonCall(self,n)end
assert(R.ensureWorldVSummonRunning(manager));assert(treeEnabled and treeWrites==1)
assert(not R.ensureWorldVSummonRunning(manager));assert(treeWrites==1)
for _,case in ipairs({'scene','inactive','clone','owner','disabled'})do
 treeEnabled=false;allowed=case~='scene';summoned=case~='inactive';clone=case=='clone';wrongOwner=case=='owner';enabled=case~='disabled'
 assert(not R.ensureWorldVSummonRunning(manager));assert(treeWrites==1)
end
''')
print('PASS: WorldV camera selects owned summon; ordinary lookups, other cameras, other managers, other threads, nested calls, clones, inactive skill and stale owners remain untouched; callbacks balance.')
