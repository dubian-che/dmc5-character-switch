-- Keep the native pause/options editor on the actor controlled by the Mod.
-- No frame polling and no direct writes to saved binding arrays.
if _G.dmc5_switch_input_menu then return _G.dmc5_switch_input_menu end
local I={hooks={},updates=0}
_G.dmc5_switch_input_menu=I
local slots={[0]=0,[1]=1,[4]=3}

local function active()
 -- PlayerManager is a scene component, not a managed singleton. Reuse the
 -- instance already captured by the loader's existing doUpdate callback.
 local loader=_G.dmc5_switch_loader
 local manager=loader and loader.manager
 local player=manager and manager:call('get_manualPlayer')
 local id=player and player:call('get_playerID')
 if slots[id]==nil then return end
 local gm=sdk.get_managed_singleton('app.GameManager')
 if gm then return gm,id end
end

function I.syncActive()
 local gm,id=active()
 if not gm then return end
 -- Native findManualPlayerID uses the mission/campaign identity, which can
 -- differ from the Mod's controllable actor (especially in Vergil mode).
 if gm:get_field('PlayingID')~=id then gm:set_field('PlayingID',id)end
 return gm,id
end

function I.open(menu)
 if not menu or not menu:call('get_IsPauseMenu')then return end
 local gm,id=I.syncActive()
 if gm then I.lastPlayer=id;I.error=nil end
end

function I.select(menu)
 if not menu or not menu:call('get_IsPauseMenu')then return end
 local gm,id=I.syncActive()
 if not gm then return end
 local slot=slots[id]
 -- ui4000.doOnOpen builds its list before calling setupKeyConfigState.
 -- Correct it before the native labels/config editor use it. A pause menu
 -- has one target; title-screen character tabs retain the native behavior.
 -- ui4000 uses config slots here: playable Vergil 4 is stored as slot 3.
 local list=menu:get_field('targetIDList')
 if list then
  local count=list:call('get_Count')
  if count==1 then
   if list:call('get_Item',0)~=slot then list:call('set_Item',0,slot)end
  else
   list:call('Clear');list:call('Add',slot)
  end
 end
 menu:set_field('playerID',slot)
 menu:set_field('playerIndex',0)
 menu:set_field('playerNum',1)
 I.lastPlayer=id;I.lastSlot=slot;I.updates=I.updates+1
end

function I.beforeApply()
 local gm=sdk.get_managed_singleton('app.GameManager')
 -- applyKeyAssign/applyKeyboardAssign call the native input refresh while
 -- still paused. Choose the active actor before it reads the saved profile.
 if gm and gm:call('get_isPauseMenu')then I.syncActive()end
end

function I.closed(menu)
 if not menu or not menu:call('get_IsPauseMenu')then return end
 local gm=I.syncActive()
 if gm then gm:call('updatePlayerPadInput')end
end

local function guarded(fn,...)
 local ok,why=pcall(fn,...)
 if not ok then I.error=tostring(why)end
end
local function install(typeName,name,pre,post)
 local ok,why=pcall(function()
  local t=sdk.find_type_definition(typeName)
  local m=t and t:get_method(name)
  assert(m,'Input menu method unavailable: '..typeName..'.'..name)
  sdk.hook(m,pre,post)
 end)
 if ok then I.hooks[#I.hooks+1]=typeName..'.'..name
 else I.installError=tostring(why)end
end
install('app.ui4000GUI','doOnOpen',function(args)
 guarded(function()I.open(sdk.to_managed_object(args[2]))end)
end,function(ret)return ret end)
install('app.ui4000GUI','setupKeyConfigState',function(args)
 guarded(function()I.select(sdk.to_managed_object(args[2]))end)
end,function(ret)return ret end)
install('app.GameManager','updatePlayerPadInput',function()guarded(I.beforeApply)end,function(ret)
 guarded(function()
  local resources=_G.dmc5_switch_resources
  if resources and resources.syncActiveInput then resources.syncActiveInput()end
 end)
 return ret
end)
install('app.ui4000GUI','doOnClose',function(args)
 guarded(function()thread.get_hook_storage().inputMenu=sdk.to_managed_object(args[2])end)
end,function(ret)
 guarded(function()I.closed(thread.get_hook_storage().inputMenu)end)
 return ret
end)
return I
