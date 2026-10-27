-- Character HUD packages are retained once per scene and toggled as whole roots.
if _G.dmc5_switch_hud then return _G.dmc5_switch_hud end
local H={version=1,stage='idle'}
_G.dmc5_switch_hud=H
local roots={[0]='pl0000Hud',[1]='pl0100Hud',[4]='pl0300Hud'}
local mainTypes={[0]='app.ui1011GUI',[1]='app.ui1015GUI',[4]='app.ui1027GUI'}
local pending,ticks=nil,0
local function sceneNow()
 local sm=sdk.get_native_singleton('via.SceneManager')
 return sdk.call_native_func(sm,sdk.find_type_definition('via.SceneManager'),'get_CurrentScene')
end
local function collect(scene)
 local groups={}
 for _,hud in ipairs(scene:call('findComponents',sdk.typeof('app.HudBase')):get_elements())do
  local tr=hud:call('get_GameObject'):call('get_Transform')
  for _=1,8 do
   if not tr then break end
   local root=tr:call('get_GameObject');local name=root:call('get_Name')
   if name=='pl0000Hud' or name=='pl0100Hud' or name=='pl0300Hud' then
    local g=groups[name] or {root=root,components={}};groups[name]=g
    table.insert(g.components,hud);break
   end
   tr=tr:call('get_Parent')
  end
 end
 return groups
end
local function advance(manager)
 local r=pending;if not r then return end
 local current=manager:call('get_manualPlayer')
 if not current or current:call('get_playerID')~=r.id then pending=nil;H.stage='cancelled';return end
 if ticks-r.start>1800 then error('HUD load timed out')end
 local scene=sceneNow();if not scene then return end
 local groups=collect(scene);local desired=groups[roots[r.id]]
 if not desired then
  if not r.loading then
   local supplier=scene:call('findComponents',sdk.typeof('app.HudSupplier')):get_elements()[1]
   if not supplier then return end
   supplier:set_field('hudIndex',-1);supplier:set_field('isPlLoaded',false)
   r.loading=true;H.stage='loading'
  end
  return
 end
 local main
 for _,h in ipairs(desired.components)do
  if h:get_type_definition():get_full_name()==mainTypes[r.id]then main=h end
 end
 if not main then return end
 local hm=sdk.get_managed_singleton('app.HudManager')
 hm:call('updateMasterPlayer');hm:call('setPlayerHUD',main)
 for name,g in pairs(groups)do
  local party=_G.dmc5_party_hud
  local enabled=(party and party.native and party.enabled) or name==roots[r.id]
  g.root:call('set_UpdateSelf',enabled);g.root:call('set_DrawSelf',enabled)
 end
 -- Reopen the retained health HUD if it was closed before being hidden.
 if main:call('get_IsClosed')then main:call('open')end
 hm:call('requestReopen')
 local party=_G.dmc5_party_hud
 if party and party.native and party.enabled then party.scan(manager) end
 H.stage='active';H.current=r.id;H.mainType=mainTypes[r.id];H.error=nil;pending=nil
end
function H.request(manager,id)
 if not roots[id]then return end
 pending={id=id,start=ticks};H.stage='requested';H.error=nil
 local ok,why=pcall(advance,manager)
 if not ok then pending=nil;H.stage='error';H.error=tostring(why)end
end
sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
 ticks=ticks+1
 if pending and ticks%10==0 then
  local ok,why=pcall(advance,sdk.to_managed_object(args[2]))
  if not ok then pending=nil;H.stage='error';H.error=tostring(why)end
 end
end,function(ret)return ret end)
return H

