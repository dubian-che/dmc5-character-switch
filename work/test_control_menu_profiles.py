"""Run real menu hooks against native pause-menu/profile lifecycle fixtures.

The native opening order and Vergil's config-slot mapping were checked in the
installed game's ui4000GUI methods; this is not an in-game UI test.
"""
import sys
from pathlib import Path

sys.path.insert(0, 'work/python-deps')
from lupa import LuaRuntime
from lua_test_support import install_module_loader

source = Path('outputs/DMC5CharacterSwitch/dmc5_switch_input_menu.lua').read_text()
lua = LuaRuntime()
install_module_loader(lua)
lua.execute('''
hooks={};stack={};installed=0
thread={get_hook_storage=function()return assert(stack[#stack])end}
sdk={
 find_type_definition=function(typeName)return {get_method=function(_,name)return typeName..'.'..name end}end,
 hook=function(method,pre,post)assert(not hooks[method]);hooks[method]={pre,post};installed=installed+1 end,
 to_managed_object=function(v)return v end,
 get_managed_singleton=function(name)
  assert(name=='app.GameManager');return gm
 end
}
function invoke(method,obj,native)
 local h=assert(hooks[method]);stack[#stack+1]={}
 h[1]({[2]=obj});local result=native and native() or 'native return'
 assert(h[2](result)==result,'hook changed native result');stack[#stack]=nil
 return result
end
function list(values)
 return {values=values,call=function(self,name,index,value)
  if name=='get_Count'then return #self.values
  elseif name=='get_Item'then return self.values[index+1]
  elseif name=='set_Item'then self.values[index+1]=value
  elseif name=='Clear'then self.values={}
  elseif name=='Add'then self.values[#self.values+1]=index
  else error(name)end
 end}
end
function scenario(id,mission,pause)
 activeID=id;missionID=mission;saves=0;refreshes=0;inputRefreshes=0
 dmc5_switch_resources={syncActiveInput=function()
  assert(refreshes>inputRefreshes,'charge rebind ran before native input replacement')
  inputRefreshes=refreshes
 end}
 profiles={pad={},keyboard={}}
 for _,kind in ipairs({'pad','keyboard'})do
  for slot=0,3 do profiles[kind][slot]=kind..slot end
 end
 player={call=function(_,name)assert(name=='get_playerID');return activeID end}
 manager={call=function(_,name)assert(name=='get_manualPlayer');return player end}
 dmc5_switch_loader={manager=manager}
 gm={PlayingID=mission,paused=pause,
  get_field=function(self,name)assert(name=='PlayingID');return self.PlayingID end,
  set_field=function(self,name,value)assert(name=='PlayingID');self.PlayingID=value end,
  call=function(self,name)
   if name=='findManualPlayerID'then return missionID end
   if name=='get_isPauseMenu'then return self.paused end
   assert(name=='updatePlayerPadInput')
   invoke('app.GameManager.updatePlayerPadInput',self,function()
    local slot=self.PlayingID==4 and 3 or self.PlayingID
    loadedPad=profiles.pad[slot];loadedKeyboard=profiles.keyboard[slot];refreshes=refreshes+1
   end)
  end}
 menu={pause=pause,playerID=0,playerIndex=0,playerNum=1,targetIDList=list({0}),
  get_field=function(self,name)return self[name]end,
  set_field=function(self,name,value)self[name]=value end,
  call=function(self,name)
   if name=='get_IsPauseMenu'then return self.pause end
   assert(name=='get_TargetPlayerID')
   return self.targetIDList and self.targetIDList.values[self.playerIndex+1] or self.playerID
  end}
end
function nativeOpen(resetIdentity)
 invoke('app.ui4000GUI.doOnOpen',menu,function()
  -- Mission identity can overwrite the earlier sync; the later hook must
  -- still correct both the fallback ID and native list before presentation.
  if resetIdentity then gm.PlayingID=missionID end
  menu.playerID=gm.PlayingID==4 and 3 or gm.PlayingID
  menu.playerIndex=0
  menu.targetIDList=list(menu.pause and {menu.playerID} or {0,1,2,3})
  menu.playerNum=#menu.targetIDList.values
  invoke('app.ui4000GUI.setupKeyConfigState',menu,function()
   shownSlot=menu:call('get_TargetPlayerID')
   shownPad=profiles.pad[shownSlot];shownKeyboard=profiles.keyboard[shownSlot]
  end)
 end)
end
function edit(kind,value)
 profiles[kind][menu:call('get_TargetPlayerID')]=value
 -- The game's own save/apply path invokes this; the Mod must not copy
 -- one character's bindings over another character's profile.
 gm.PlayingID=missionID;gm:call('updatePlayerPadInput');saves=saves+1
end
''')
lua.globals().I = lua.execute(source)

for actor, slot in ((0, 0), (1, 1), (4, 3)):
    for mission in (0, 1, 4):
        for reset in (False, True):
            lua.globals().scenario(actor, mission, True)
            lua.globals().nativeOpen(reset)
            lua.globals().expectedSlot = slot
            lua.execute('''
assert(shownSlot==expectedSlot and menu.playerID==expectedSlot)
assert(menu.playerIndex==0 and menu.playerNum==1)
assert(#menu.targetIDList.values==1 and menu.targetIDList.values[1]==expectedSlot)
assert(shownPad=='pad'..expectedSlot and shownKeyboard=='keyboard'..expectedSlot)
assert(gm.PlayingID==missionID and I.lastPlayer==activeID and I.lastSlot==expectedSlot)
edit('pad','custom pad');assert(loadedPad=='custom pad' and gm.PlayingID==missionID)
edit('keyboard','custom keyboard');assert(loadedKeyboard=='custom keyboard')
for slot=0,3 do
 if slot~=expectedSlot then
  assert(profiles.pad[slot]=='pad'..slot and profiles.keyboard[slot]=='keyboard'..slot)
 end
end
invoke('app.ui4000GUI.doOnClose',menu,function()
 gm.PlayingID=missionID;gm.paused=false;saves=saves+1
end)
assert(gm.PlayingID==missionID and refreshes==3 and saves==3)
assert(inputRefreshes==refreshes)
assert(loadedPad=='custom pad' and loadedKeyboard=='custom keyboard')
-- Switching to another actor and back must read the saved independent sets.
local original=activeID
for _,id in ipairs({0,1,4,original})do
 activeID=id;gm.PlayingID=missionID;dmc5_switch_runtime.withInputProfile(gm,id,function()gm:call('updatePlayerPadInput')end);assert(gm.PlayingID==missionID)
 local slot=id==4 and 3 or id
 assert(loadedPad==(slot==expectedSlot and 'custom pad' or 'pad'..slot))
 assert(loadedKeyboard==(slot==expectedSlot and 'custom keyboard' or 'keyboard'..slot))
end
assert(I.error==nil and I.installError==nil)
''')

lua.execute('''
-- Title options retain all native character tabs, even with a stale actor.
scenario(4,0,false);nativeOpen(false)
assert(gm.PlayingID==0 and menu.playerNum==4 and shownSlot==0)
menu.playerIndex=2;invoke('app.ui4000GUI.setupKeyConfigState',menu)
assert(menu.playerIndex==2 and menu:call('get_TargetPlayerID')==2)
invoke('app.ui4000GUI.doOnClose',menu);assert(refreshes==0)
-- A refresh outside the pause menu retains the caller's selected identity.
gm.PlayingID=1;gm:call('updatePlayerPadInput');assert(gm.PlayingID==1)
-- Unrelated playable actors and absent game objects are left to the game.
for _,id in ipairs({2,3,5})do
 scenario(id,0,true);nativeOpen(false);assert(gm.PlayingID==0 and shownSlot==0)
end
scenario(4,0,true);player=nil;nativeOpen(false);assert(shownSlot==0)
scenario(4,0,true);dmc5_switch_loader.manager=nil;nativeOpen(false);assert(shownSlot==0)
scenario(4,0,true);dmc5_switch_loader=nil;nativeOpen(false);assert(shownSlot==0)
scenario(4,0,true);gm=nil;invoke('app.ui4000GUI.setupKeyConfigState',menu);assert(menu.playerID==0)
-- List fallback and rebuilding cover initialization edge cases.
scenario(4,0,true);menu.targetIDList=nil
invoke('app.ui4000GUI.setupKeyConfigState',menu);assert(menu:call('get_TargetPlayerID')==3)
menu.targetIDList=list({});invoke('app.ui4000GUI.setupKeyConfigState',menu)
assert(menu:call('get_TargetPlayerID')==3 and #menu.targetIDList.values==1)
menu.targetIDList=list({0,1,2,3});invoke('app.ui4000GUI.setupKeyConfigState',menu)
assert(menu:call('get_TargetPlayerID')==3 and #menu.targetIDList.values==1)
-- A managed-object failure must not escape the hook or change native returns.
menu.call=function()error('disposed menu')end
invoke('app.ui4000GUI.setupKeyConfigState',menu);assert(I.error:find('disposed menu'))
assert(installed==7 and #I.hooks==5 and #stack==0)
''')
lua.execute(source)
assert lua.globals().installed == 7, 'module reload duplicated hooks'

missing = LuaRuntime()
install_module_loader(missing)
missing.execute('dmc5_switch_runtime={permits=function()return false end}')
missing.execute('sdk={find_type_definition=function()return nil end}')
result = missing.execute(source)
assert result.installError and len(result.hooks) == 0
print('PASS: Nero/Dante/Vergil native menu selection; independent pad/keyboard saves; mission-ID reset repaired; close refresh; title tabs/unsupported actors preserved; safe hook failures; no duplicate hooks.')
