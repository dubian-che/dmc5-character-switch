import sys
from pathlib import Path
sys.path.insert(0,'work/python-deps')
from lupa import LuaRuntime
from lua_test_support import install_module_loader
lua=LuaRuntime()
install_module_loader(lua)
lua.execute('sdk={find_type_definition=function() return {get_method=function()return {}end}end,hook=function()end}')
module=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_regen.lua').read_text())
lua.globals().R=module
lua.execute('''
local players={};local writes=0
for _,id in ipairs({0,1,4})do
 local p={id=id,hp=12345,maxHp=20000,dt=5000,cap=10000}
 function p:call(method,value)
  if method=='get_playerID'then return self.id
  elseif method=='get_hp'then return self.hp
  elseif method=='get_maxHp'then return self.maxHp
  elseif method=='set_hp'then self.hp=value;healthWrites=healthWrites+1
  elseif method=='get_devilTriggerGauge'then return self.dt
  elseif method=='get_maxDevilTriggerGauge'then return self.cap
  elseif method=='set_devilTriggerGauge'then self.dt=value;writes=writes+1
  else error(method)end
 end
 players[id]=p
end
local manager={active=0}
function manager:call(method,id)
 if method=='get_manualPlayer'then return players[self.active]end
 if method=='getPlayerByID'then return players[id]end
 error(method)
end
for _,fps in ipairs({30,60,75,144})do
 writes=0;healthWrites=0;R.pending={};R.elapsed=0;R.lastActive=nil
 for _,p in pairs(players)do p.dt=5000;p.hp=12345 end
 for i=1,fps*5 do R.update(manager,1/fps,false)end
 R.flush(manager)
 assert(players[0].dt==5000)
 assert(math.abs(players[1].dt-6000)<0.00001)
 assert(math.abs(players[4].dt-6000)<0.00001)
 assert(players[0].hp==12345)
 assert(math.abs(players[1].hp-14845)<.00001 and math.abs(players[4].hp-14845)<.00001)
 assert(writes<=100,'regen writes more than ten times/second per reserve')
 assert(healthWrites<=100,'HP regen exceeded the shared flush cadence')
end
R.update(manager,0.1,true);assert(math.abs(players[1].dt-6000)<0.00001)
players[1].dt=9999;R.update(manager,0.1,false);assert(players[1].dt==10000)
manager.active=1;local before=players[1].dt;R.update(manager,0.1,false);assert(players[1].dt==before)
assert(players[0].dt>5000)
players[4].hp=0;local dead=players[4].dt;R.update(manager,0.1,false);assert(players[4].dt==dead)
assert(players[0].hp>12345 and players[1].hp>12345)
players[4].hp=12345;manager.active=0;R.pending={};R.elapsed=0;R.lastActive=nil
for _,p in pairs(players)do p.dt=5000 end
for i=1,375 do R.update(manager,1/75,false)end
assert(math.abs(players[1].dt+(R.pending[1] or 0)-6000)<0.00001)
assert(6000-players[1].dt<20)
R.flush(manager);assert(math.abs(players[1].dt-6000)<0.00001)
-- A mid-batch handoff must preserve exactly each actor's earned time.
R.pending={};R.elapsed=0;R.lastActive=nil
for _,p in pairs(players)do p.dt=5000 end
R.update(manager,.04,false);manager.active=1;R.update(manager,.06,false);R.flush(manager)
assert(math.abs(players[0].dt-5012)<.00001)
assert(math.abs(players[1].dt-5008)<.00001)
assert(math.abs(players[4].dt-5020)<.00001)
-- Two seconds gives one HP segment to reserves, even with full ordinary DT.
R.pending={};R.elapsed=0;R.lastActive=nil;manager.active=0
for _,p in pairs(players)do p.hp=10000;p.dt=10000 end
for i=1,120 do R.update(manager,1/60,false)end
R.flush(manager)
assert(players[0].hp==10000 and math.abs(players[1].hp-11000)<.00001 and math.abs(players[4].hp-11000)<.00001)
local saved=players[1].hp
for i=1,120 do R.update(manager,1/60,true)end
assert(players[1].hp==saved,'pause counted as reserve recovery time')
players[1].hp=19999;players[4].hp=0
R.update(manager,.1,false);R.flush(manager)
assert(players[1].hp==20000 and players[4].hp==0,'HP exceeded max or revived dead reserve')
-- Earned fractions belong to the actor that was in reserve before handoff.
for _,p in pairs(players)do p.hp=10000 end
R.pending={};R.elapsed=0;R.lastActive=nil;manager.active=0
R.update(manager,.04,false);manager.active=1;R.update(manager,.06,false);R.flush(manager)
assert(math.abs(players[0].hp-10030)<.00001 and math.abs(players[1].hp-10020)<.00001 and math.abs(players[4].hp-10050)<.00001)
-- Transfer loading must neither heal nor bank time for the destination.
dmc5_switch_palace={canRegen=function()return false end}
local before=players[4].hp
for i=1,120 do R.update(manager,1/60,false)end
R.flush(manager);assert(players[4].hp==before and next(R.pending)==nil)
dmc5_switch_palace=nil
R.update(manager,.1,false);R.flush(manager)
assert(math.abs(players[4].hp-before-50)<.00001)
''')
print('PASS: reserve HP 1000/2 sec and ordinary DT 1000/5 sec at 30/60/75/144 FPS; shared bounded writes; full-DT healing, caps, no revival, pause and exact handoff credits.')
