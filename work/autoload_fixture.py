import sys
from pathlib import Path
sys.path.insert(0, 'work/python-deps')
from lupa import LuaRuntime

SOURCE = Path('outputs/DMC5CharacterSwitch')


def make_game(initial=0, fps=60, config=None):
    lua = LuaRuntime()
    lua.globals().initial_id = initial
    lua.globals().fps = fps
    lua.globals().key_config = lua.table_from(config) if config is not None else None
    lua.execute('''
paused=false;event=false;thinking=true;stalled=false;stealControl=false;locationBusy=false;clock=0;ownerRestores=0;excludedCount=0;mode=3;missionNo=1;campaignID=initial_id
unregistered={}
profiles={};players={};states={};loads={};preloads={};loadAt={};finishAt={};switches=0;initializations=0;scans=0
hooks={};nativeHooks={};frames={};controller_loads=0;hookStorage={}
thread={get_hook_storage=function()return hookStorage end}
function actor(id)
 local p={id=id,visible=true,enabled=true,componentEnabled=true,updating=true,worldEnabled=true,initialized=0,paused=false,meshReady=true,hp=20000,weaponS=4,weaponL=0}
 local world={call=function(_,n,v)
  if n=='get_Enabled'then return p.worldEnabled end
  assert(n=='set_Enabled');p.worldEnabled=v
 end}
 local med={call=function(_,name,value)
  if name=='set_updateSelf'then p.updating=value end
  if name=='set_drawSelf'then p.visible=value;p.medDraw=value end
  if name=='get_drawSelf'then if p.medDraw~=nil then return p.medDraw else return p.visible end end
  if name=='get_updateSelf'then return p.updating end
 end}
 local work={call=function()return 1/fps end}
 local hit={get_field=function()return work end}
 function p:get_field(name)
  if name=='IsDoppel'then return self.isDoppel end
  if name=='IsEnemyDante'then return self.enemyDante end
 end
 function p:call(name,value)
  if name=='get_playerID'then return self.id
  elseif name=='get_Enable'then return self.enabled
  elseif name=='get_Enabled'then return self.componentEnabled
  elseif name=='get_hp'then return self.hp
  elseif name=='get_isDevilTrigger'or name=='get_isTheDevilTrigger'then return self.devil or false
  elseif name=='get_currentWeaponS'then return self.weaponS
  elseif name=='get_currentWeaponL'then return self.weaponL
  elseif name=='get_bodyMeshList'then return {
   get_size=function()return self.meshReady and 1 or 0 end,
   get_element=function()return self.meshReady and self.meshBound~=false and {}or nil end}
  elseif name=='get_cachedHitController'then return hit
  elseif name=='get_cachedCharacterController'then if not self.noWorld then return world end
  elseif name=='get_isThinkEnable'then return thinking
  elseif (name=='get_isEventMove'or name=='get_isEventRun')then return event or self.eventRun or false
  elseif name=='get_cachedActivateMediator'then return med
  elseif name=='get_GameObject'then return {call=function(_,n)if n=='get_UpdateSelf'then return p.updating end;assert(n=='get_DrawSelf');return p.visible end}
  elseif name=='MissionInitPlayerData'then self.initialized=self.initialized+1
  elseif name=='resetParameters'then
  elseif name=='pausePlayer'then self.paused=true
  elseif name=='set_Enable'then self.enabled=value
  else error('Unexpected player call '..name)end
 end
 return p
end
players[initial_id]=actor(initial_id);active=players[initial_id]
local function roster()
 local out={}
 for _,id in ipairs({0,1,2,4})do if players[id]then out[#out+1]=players[id]end end
 for _,p in ipairs(unregistered)do out[#out+1]=p end
 return out
end
manager={call=function(_,name,id)
 if name=='get_manualPlayer'then return active
 elseif name=='getPlayerByID'then return players[id]
 elseif name=='getPlayerNum'then return #roster()
 elseif name=='getPlayer'then return roster()[id+1]
 else error('Unexpected manager call '..name)end
end}
local list={call=function(_,name,index)
 local ids={};for _,id in ipairs({0,1,2,4})do if states[id]~=nil then ids[#ids+1]=id end end
 if name=='get_Count'then scans=scans+1;return #ids end
 local id=ids[index+1]
 return {get_field=function(_,key)if key=='RequestedPlayerID'then return id elseif key=='RequestedCostumeID'then return profiles[id]and profiles[id][1]or 0 elseif key=='RequestedSituationID'then return profiles[id]and profiles[id][2]or 0 else return states[id]end end}
end}
native={get_field=function()return list end,call=function(_,name,id)
 if name=='requestPreloadPlayerResource'then
  preloads[id]=(preloads[id] or 0)+1
  if states[id]==nil then states[id]=2 end
 elseif name=='isReadyPreloadPlayerResource'then
  return states[id]==2 and (id~=4 or states[0]~=nil)
 elseif name=='requestLoadPlayerResource'then
  assert(states[id]==2,'duplicate/premature load request')
  loads[id]=(loads[id] or 0)+1;states[id]=3;loadAt[id]=clock;players[id]=actor(id)
  if stealControl then active=players[id];dmc5_switch_runtime.invalidate()end
 elseif name=='isReadyPlayerResource'then return states[id]==6
 elseif name=='requestFinishPlayerResource'then states[id]=7;finishAt[id]=clock
 else error('Unexpected loader call '..name)end
end}
sdk={hook=function(method,pre,post)
 if method=='app.PlayerManager.doUpdate'then hooks[#hooks+1]=pre
 else nativeHooks[method]={pre,post}end
 end,
 find_type_definition=function(name)return {get_method=function(_,method)return name..'.'..method end}end,
 to_managed_object=function(v)return v end,
 get_managed_singleton=function(name)
  if name=='app.GameManager'then return {call=function(_,method)
   if method=='get_gameMode'then return mode elseif method=='get_missionNo'then return missionNo elseif method=='findManualPlayerID'then return campaignID end;return paused
  end}end
  if name=='app.AdditionalPlayerLoadManager'then return native end
  if name=='app.LocationEnvManager'then return {call=function(_,n)assert(n=='get_isBusy');return locationBusy end}end
  error(name)
 end}
re={on_frame=function(fn)frames[#frames+1]=fn end,on_draw_ui=function()error('release registered a debug panel')end}
key_down={};config_reads=0
reframework={is_key_down=function(_,key)return key_down[key] or false end}
json={load_file=function()config_reads=config_reads+1;return key_config end,
 dump_file=function()error('unexpected background file I/O')end}
core={version=9,names={[0]='Nero',[1]='Dante',[4]='Vergil'},
 parkReserve=function(_,p)
  if p==active or p.eventRun or p.isDoppel or p.enemyDante then return false end
  if p.enabled or p.visible or p.updating then
   p.parkings=(p.parkings or 0)+1
   p.enabled=false;p.visible=false;p.medDraw=false;p.updating=false;p.componentEnabled=false;p.worldEnabled=false;p.paused=true
  end
  return true
 end,
 recoverSelected=function(_,p)
  assert(active==p and (p.id==0 or p.id==1 or p.id==4) and not event and not paused)
  p.recoveries=(p.recoveries or 0)+1;p.enabled=true;p.visible=true;p.paused=false
 end,
 parkNonParty=function(_,p)
  assert(p.id==2 and active~=p and not paused and not event)
  if p.eventRun then return false end
  excludedCount=excludedCount+1;p.visible=false;p.medDraw=false;p.enabled=false;p.updating=false;p.paused=true;return true
 end,
 restoreLoadOwner=function(_,p)active=p;ownerRestores=ownerRestores+1;dmc5_switch_runtime.invalidate()end,
 hideReserve=function(_,p)assert(p~=active);p.visible=false;p.medDraw=false;p.hideCalls=(p.hideCalls or 0)+1;return true end,
 prepareReserve=function(_,p)
  assert(p~=active and states[p.id]==6,'prepared actor before native readiness')
  assert(p.initialized==0,'actor initialized more than once')
  p.initialized=p.initialized+1;initializations=initializations+1
  p.visible=false;p.paused=true;p.enabled=false
 end,
 switch=function(_,id)
  local p=players[id];assert(dmc5_switch_loader.ready(manager,id),'switch before complete')
  if loadAt[id]then assert(states[id]==6 and p.initialized==1)end
  active.visible=false;active.enabled=false;active.componentEnabled=false;active.updating=false;active.paused=true
  active=p;p.visible=true;p.enabled=true;p.componentEnabled=true;p.updating=true;p.paused=false
  switches=switches+1;dmc5_switch_runtime.invalidate();return {id=id}
 end}
function tick(count)
 for n=1,count do
  if not paused and not event then
   clock=clock+1/fps
   for id,t in pairs(loadAt)do if not stalled and states[id]==3 and clock-t>=.35 then states[id]=6 end end
   for id,t in pairs(finishAt)do if clock-t>=.2 then states[id]=nil;finishAt[id]=nil;loadAt[id]=nil end end
  end
  for _,fn in ipairs(frames)do fn()end
  for _,fn in ipairs(hooks)do fn({[2]=manager})end
 end
end
''')

    def load(path):
        name = Path(path).name
        if name == 'dmc5_switch_core.lua':
            return lua.globals().core
        if name == 'dmc5_switch_controller.lua':
            lua.globals().controller_loads += 1
            return lua.table()
        return lua.execute((SOURCE / name).read_text())

    lua.globals().dofile = load
    load('dmc5_switch_runtime.lua')
    load('dmc5_switch_lifecycle.lua')
    lua.globals().S = load('dmc5_live_switch.lua')
    return lua
