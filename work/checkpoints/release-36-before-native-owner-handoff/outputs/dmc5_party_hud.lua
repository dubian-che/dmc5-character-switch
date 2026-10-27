-- Native party HUD: retained game gauges, without portraits.
local H=_G.dmc5_party_hud or {}
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
_G.dmc5_party_hud=H
H.version=4;H.enabled=true;H.native=true;H.render=function()end
H.entries=H.entries or {}
H.scanElapsed=0;H.gaugeElapsed=0
local configs={['app.ui1011GUI']={0,0},['app.ui1015GUI']={1,1},['app.ui1027GUI']={4,2}}
local roots={pl0000Hud=0,pl0100Hud=1,pl0300Hud=4}
local indices={[0]=0,[1]=1,[4]=2}
local positions={[0]=35,[1]=305,[2]=425}
local sceneType,hudType
local function sceneNow()
 sceneType=sceneType or sdk.find_type_definition('via.SceneManager')
 local sm=sdk.get_native_singleton('via.SceneManager')
 return sdk.call_native_func(sm,sceneType,'get_CurrentScene')
end
function H.scan(manager)
 if not runtime.permits(manager)then return end
 local active=manager:call('get_manualPlayer')
 H.active=active and active:call('get_playerID') or H.active
 local scene=sceneNow();if not scene then return end
 if H.scene~=scene then H.scene=scene;H.entries={} end
 hudType=hudType or sdk.typeof('app.HudBase')
 local seen={}
 for _,hud in ipairs(scene:call('findComponents',hudType):get_elements())do
  local cfg=configs[hud:get_type_definition():get_full_name()]
  if cfg then
   local id,index=cfg[1],cfg[2];seen[id]=true
   local e=H.entries[id]
   if not e or e.hud~=hud then e={hud=hud,id=id,index=index,zoom=0};H.entries[id]=e end
   local all=hud:get_field('c_all')
   if e.all~=all then e.all=all;e.layoutDirty=true;e.shown=nil end
   local tr=hud:call('get_GameObject'):call('get_Transform');e.chain={}
   for j=1,8 do
    if not tr then break end
    local go=tr:call('get_GameObject');table.insert(e.chain,go)
    if roots[go:call('get_Name')]then break end
    tr=tr:call('get_Parent')
   end
   -- Preserve the complete native composite, including its glass mesh and
   -- animation panels. Only the common root participates in party layout.
   e.bindingDirty=true;e.layoutDirty=true
  else
   -- Secondary weapon displays belong only to the controlled character.
   local tr=hud:call('get_GameObject'):call('get_Transform')
   for j=1,8 do
    if not tr then break end
    local id=roots[tr:call('get_GameObject'):call('get_Name')]
    if id then local go=hud:call('get_GameObject');go:call('set_DrawSelf',id==H.active);go:call('set_UpdateSelf',id==H.active);break end
    tr=tr:call('get_Parent')
   end
  end
 end
 for id in pairs(H.entries)do if not seen[id]then H.entries[id]=nil end end
 H.scanElapsed=0
end
function H.update(manager)
 if not runtime.permits(manager)then H.entries={};H.scene=nil;H.lastPlayer=nil;H.lastActive=nil;return end
 local c=runtime.get(manager);local active,id=c.active,c.id
 if id~=0 and id~=1 and id~=4 then
  H.entries={};H.scene=nil;H.lastPlayer=nil;H.lastActive=nil;return
 end
 local changed=H.lastActive~=id or H.lastPlayer~=active
 local resumed=H.paused and not c.menuPaused
 H.active=id;H.lastActive=id;H.lastPlayer=active;H.paused=c.menuPaused
 local dt=runtime.delta(c)
 H.scanElapsed=H.scanElapsed+dt;H.gaugeElapsed=H.gaugeElapsed+dt
 local complete=H.entries[0] and H.entries[1] and H.entries[4]
 if changed or resumed or H.scanElapsed>=(complete and 3 or .5) then H.scan(manager)end
 if H.paused then return end
 local refresh=changed or resumed or H.gaugeElapsed>=.1-1e-8
 if refresh then H.gaugeElapsed=math.max(0,H.gaugeElapsed-.1*math.floor((H.gaugeElapsed+1e-8)/.1)) end
 for pid,e in pairs(H.entries)do
  if refresh or e.bindingDirty then
   local player=manager:call('getPlayerByID',pid)
   if player and e.all then
    if e.bindingDirty or e.player~=player then
     for _,go in ipairs(e.chain)do go:call('set_DrawSelf',true);go:call('set_UpdateSelf',true)end
     e.hud:set_field('player',player);e.player=player;e.bindingDirty=false
    end
    -- The selected HUD retains its native per-frame update. Only reserve
    -- gauges need an explicit refresh, at most ten times per gameplay second.
    if pid~=id or changed then e.hud:call('updateHpGauge');e.hud:call('updateDevilTrigger')end
   end
  end
 end
 H.stage='active';H.error=nil
end
function H.layout()
 if runtime.manager and not runtime.permits()then return end
 if not H.enabled then return end
 for id,e in pairs(H.entries)do
  if e.all then
   local goal=id==H.active and 1 or 0
   local activeIndex=indices[H.active] or 0
   local targetY=positions[(e.index-activeIndex)%3]
   local visible=not H.paused
   if e.shown~=visible then e.all:call('set_Visible',visible);e.shown=visible end
   if e.layoutDirty or e.zoom~=goal or e.y~=targetY or (e.velocity or 0)~=0 then
   e.zoom=e.zoom+(goal-e.zoom)*.18
   if math.abs(goal-e.zoom)<.0001 then e.zoom=goal end
   local scale=.32+.68*e.zoom
   e.y=e.y or targetY;e.velocity=e.velocity or 0
   e.velocity=(e.velocity+(targetY-e.y)*.14)*.62
   e.y=e.y+e.velocity
   if math.abs(targetY-e.y)<.05 and math.abs(e.velocity)<.05 then e.y=targetY;e.velocity=0 end
   local y=e.y

   -- HUDs contain rotated 3D glass/Exceed meshes as well as 2D gauges.
   -- Scale depth with width/height so reserves retain their native proportions.
   e.all:call('set_Position',Vector3f.new(18*(1-e.zoom),y,0));e.all:call('set_Scale',Vector3f.new(scale,scale,scale))
   e.layoutDirty=false
   end
  end
 end
end
if not H.nativeHooked then
 sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
  local ok,why=pcall(H.update,sdk.to_managed_object(args[2]));if not ok then H.error=tostring(why);H.stage='error';H.entries={};H.lastPlayer=nil end
 end,function(ret)return ret end)
 re.on_frame(function()local ok,why=pcall(H.layout);if not ok then H.error=tostring(why);H.stage='error';H.entries={};H.lastPlayer=nil end end)
 H.nativeHooked=true
end
return H



