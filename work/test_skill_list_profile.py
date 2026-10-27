"""Match ui3110's verified native opening order and four-slot skill data."""
from pathlib import Path
from lupa import LuaRuntime

lua=LuaRuntime()
lua.execute('''
hooks={};writes=0;actorID=0;nativeID=0;paused=true;profileCount=4
gm={PlayingID=0,call=function(_,n)
 assert(n=='get_isPauseMenu');return paused
end}
local player={call=function(_,n)assert(n=='get_playerID');return actorID end}
manager={call=function(_,n)assert(n=='get_manualPlayer');return player end}
dmc5_switch_runtime={manager=manager,permits=function(m)
 return m==manager and (actorID==0 or actorID==1 or actorID==4)and
  (nativeID==0 or nativeID==1 or nativeID==4)
end}
dofile=function()return dmc5_switch_runtime end
sdk={get_managed_singleton=function(n)assert(n=='app.GameManager');return gm end,
 find_type_definition=function(n)return {get_method=function(_,m)return n..'.'..m end}end,
 hook=function(m,pre,post)assert(not hooks[m]);hooks[m]={pre=pre,post=post}end,
 to_managed_object=function(v)return v end}
menu={playerID=0,get_field=function(_,n)
 assert(n=='SkillData');if profileCount<0 then return nil end
 return {call=function(_,m)assert(m=='get_Count');return profileCount end}
end,set_field=function(self,n,v)assert(n=='playerID');self.playerID=v;writes=writes+1 end}
function nativeOpen(fail)
 -- Real doOnOpen reads the native hero and maps Vergil to slot3 BEFORE
 -- calling setupSkillData. Hooking before doOnOpen would be overwritten.
 menu.playerID=nativeID==4 and 3 or nativeID
 local hook=hooks['app.ui3110GUI.setupSkillData'];hook.pre({[2]=menu})
 shownSlot=menu.playerID;movieSlot=menu.playerID
 if fail then error('native list construction failure')end
 assert(hook.post('native return')=='native return')
end
''')
source=Path('outputs/DMC5CharacterSwitch/dmc5_switch_input_menu.lua').read_text(encoding='utf-8')
lua.globals().I=lua.execute(source)
for actor,slot in [(0,0),(1,1),(4,3)]:
    for native in [0,1,4]:
        lua.globals().actorID=actor;lua.globals().nativeID=native
        lua.globals().gm.PlayingID=native
        lua.globals().expectedSlot=slot
        lua.execute('''
        nativeOpen(false)
        assert(shownSlot==expectedSlot and movieSlot==expectedSlot)
        assert(gm.PlayingID==nativeID and I.skillPlayer==actorID)
        assert(not pcall(nativeOpen,true)and gm.PlayingID==nativeID)
        ''')
lua.execute('''
-- Gallery/title contexts, native V campaigns and unsupported actors remain native.
actorID=1;nativeID=0;paused=false;local before=writes
nativeOpen(false);assert(shownSlot==0 and writes==before)
paused=true
for _,id in ipairs({2,3})do actorID=id;nativeOpen(false);assert(writes==before)end
actorID=1;nativeID=2;nativeOpen(false);assert(shownSlot==2 and writes==before)
actorID=4;nativeID=0;profileCount=3;nativeOpen(false)
assert(shownSlot==0 and writes==before and I.skillWarning)
profileCount=-1;nativeOpen(false);assert(writes==before)
profileCount=4;nativeOpen(false);assert(shownSlot==3 and not I.skillWarning)
''')
count=len(list(lua.globals().hooks.keys()))
lua.execute(source)
assert len(list(lua.globals().hooks.keys()))==count
print('PASS: skill categories and previews follow Nero/Dante/Vergil after native hero assignment; native Vergil slot3, campaign identity, V/title and missing-data guards preserved; no repeated hooks')
