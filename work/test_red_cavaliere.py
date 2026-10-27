"""Run the actual equipment policy and native selection hook with named enums."""
from pathlib import Path
from lupa import LuaRuntime
from lua_test_support import install_module_loader

l = LuaRuntime()
install_module_loader(l)
l.execute('''
hooks={};enumReads=0
local enums={['app.PlayerDante.WeaponS']={Emperor=42,EmperorRB=73},
 ['app.PlayerDante.Weapon']={EmperorRBL=201,EmperorRBR=205}}
sdk={find_type_definition=function(name)
 if enums[name]then return {get_field=function(_,key)
  assert(enums[name][key]);return {get_data=function(_,obj)
   assert(obj==nil);enumReads=enumReads+1;return enums[name][key]
  end}
 end}end
 return {get_method=function(_,key)return key end}
end,hook=function(method,pre,post)hooks[method]={pre=pre,post=post}end,
to_managed_object=function(p)return p end,to_int64=function(n)return n end,to_ptr=function(n)return n end}
function actor(id,weapon,available,enemy)
 local p={id=id,weapon=weapon,available=available,enemy=enemy or false,
  slots={7,42,19},slot=1,changes=0,writes=0,hp=8000,dt=3500}
 local list={call=function(_,name,index,value)
  if name=='get_Count'then return #p.slots
  elseif name=='get_Item'then return p.slots[index+1]
  elseif name=='set_Item'then p.slots[index+1]=value;p.writes=p.writes+1
  else error(name)end
 end}
 local container={call=function(_,name,key)
  assert(name=='ContainsKey' and (key==201 or key==205));return p.available
 end}
 function p:get_field(name)assert(name=='IsEnemyDante');return self.enemy end
 function p:call(name,a,b)
  if name=='get_playerID'then return self.id
  elseif name=='get_weaponContainer'then return container
  elseif name=='get_slotWeaponS'then return list
  elseif name=='get_currentWeaponS'then return self.weapon
  elseif name=='get_weaponS_ID'then return self.slot
  elseif name=='changeWeaponS'then
   local args={[2]=self,[3]=a,[4]=b};hooks.changeWeaponS.pre(args)
   self.weapon=args[3];self.slot=args[4];self.changes=self.changes+1
  else error('Unexpected actor mutation: '..name)end
 end
 return p
end
''')
l.globals().P = l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_progression.lua').read_text())
l.execute('''
local active={call=function()return 1 end}
dmc5_switch_runtime.manager={call=function()return active end}
sdk.get_managed_singleton=function()return {call=function(_,name)assert(name=='findManualPlayerID');return 1 end}end
''')
l.execute('''
local p=actor(1,42,true)
assert(P.lockRedBike(p))
assert(p.slots[1]==7 and p.slots[2]==73 and p.slots[3]==19)
assert(p.weapon==73 and p.slot==1 and p.changes==1 and p.writes==1)
P.lockRedBike(p);assert(p.changes==1 and p.writes==1,'repeated entry reset equipment')
p:call('changeWeaponS',42,2)
assert(p.weapon==73 and p.slot==2,'cycling selected the black motorcycle')
p:call('changeWeaponS',7,0);assert(p.weapon==7,'unrelated weapon redirected')
P.lockRedBike(p);assert(p.weapon==7,'switching to Dante forced motorcycle over another weapon')
assert(p.hp==8000 and p.dt==3500)
assert(enumReads==4,'named enum values were repeatedly resolved')
for _,id in ipairs({0,4})do
 local other=actor(id,42,true)
 assert(not P.lockRedBike(other) and other.writes==0 and other.changes==0)
end
local enemy=actor(1,42,true,true)
assert(not P.lockRedBike(enemy));enemy:call('changeWeaponS',42,0);assert(enemy.weapon==42)
local absent=actor(1,42,false)
assert(not P.lockRedBike(absent) and absent.slots[2]==42 and absent.weapon==42)
absent:call('changeWeaponS',42,0);assert(absent.weapon==42 and P.redBikeWarning)
absent.available=true;assert(P.lockRedBike(absent) and absent.weapon==73 and P.redBikeWarning==nil)
assert(hooks.changeWeaponS.post(123)==123,'native return was replaced')
''')
print('PASS: named red-bike enums; runtime slots/current bike and future cycling use Cavaliere R; unrelated weapons, other actors, bosses and absent resources preserved; idempotent and no polling.')
