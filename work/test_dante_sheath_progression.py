"""Late skill unlock initializes the native DSD sheath channel exactly once."""
from pathlib import Path
from lupa import LuaRuntime
from lua_test_support import install_module_loader

l=LuaRuntime();install_module_loader(l)
l.execute('''
local names={'app.ChargeParameter','app.PadInput','System.UInt32','System.Int32','System.Int32'}
local params={};for i,n in ipairs(names)do params[i]={get_full_name=function()return n end}end
local method={get_name=function()return 'setData'end,get_param_types=function()return params end,
 call=function(_,c,p,input,flag,start,limit)
  assert(flag==1 and start==c.owner.level-1 and limit==2147483647)
  c.writes=c.writes+1
  if c.fail then error('native setData failure')end
  c.parameter=p;c.input=input;c.flag=flag;c.timer=0
 end}
sdk={hook=function()end,find_type_definition=function()return {
 get_method=function(_,n)return n end,get_methods=function()return {method}end}end}
function actor(id,level)
 local a={id=id,level=level,input={},parameter={},setups=0}
 local c={owner=a,writes=0,flag=0,timer=0};a.charge=c
 function c:call(n)
  if n=='get_parameter'then return self.parameter
  elseif n=='get_padInput'then return self.input
  elseif n=='get_padInputFlag'then return self.flag
  else error('unexpected charge mutation '..n)end
 end
 local sword={get_field=function(_,n)assert(n=='SheathCharge');return a.level end}
 local data={get_field=function(_,n)assert(n=='Sword');return sword end}
 local skills={get_field=function(_,n)assert(n=='DS_SheathExpansion');return a.parameter end}
 local characteristic={get_field=function(_,n)assert(n=='ChargeSkill');return skills end}
 function a:get_field(n)
  if n=='IsEnemyDante'then return self.enemy
  elseif n=='<chargeSheath>k__BackingField'then return self.charge
  elseif n=='CharacteristicParameter'then return characteristic
  else error(n)end
 end
 function a:call(n)
  if n=='get_playerID'then return self.id
  elseif n=='get_playerData'then return data
  elseif n=='get_padInput'then return self.input
  elseif n=='setupChargeSheath'then self.setups=self.setups+1;self.callbacks={native=true}
  else error(n)end
 end
 return a
end
''')
l.globals().P=l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_progression.lua').read_text())
l.execute('''
-- Native construction saw an unpurchased skill; allOpen happens afterwards.
local p=actor(1,0)
assert(not P.refreshDanteSheath(p)and p.charge.writes==0)
p.level=2
assert(P.refreshDanteSheath(p))
assert(p.charge.parameter==p.parameter and p.charge.input==p.input)
assert(p.charge.writes==1 and p.setups==1 and p.callbacks.native)
local callbacks=p.callbacks;p.charge.timer=3.25
for i=1,1000 do assert(not P.refreshDanteSheath(p))end
assert(p.charge.timer==3.25 and p.callbacks==callbacks and p.setups==1)
-- Native new actor/floor starts a fresh lifecycle, without reusing old data.
local nextActor=actor(1,1);assert(P.refreshDanteSheath(nextActor))
for _,id in ipairs({0,2,4})do
 local other=actor(id,2);assert(not P.refreshDanteSheath(other)and other.charge.writes==0)
end
local enemy=actor(1,2);enemy.enemy=true;assert(not P.refreshDanteSheath(enemy))
local absent=actor(1,2);absent.parameter=nil
assert(not P.refreshDanteSheath(absent)and absent.setups==0)
local partial=actor(1,2);partial.charge.flag=1
assert(not P.refreshDanteSheath(partial)and partial.setups==0)
local failed=actor(1,2);failed.charge.fail=true
assert(not pcall(P.refreshDanteSheath,failed))
for i=1,1000 do assert(not P.refreshDanteSheath(failed))end
assert(failed.charge.writes==1 and failed.setups==0)
''')
print('PASS: DSD native sheath initialization after late unlock; native start level, callbacks, held-charge preservation, replacement actors, other heroes, enemy Dante and bounded failures.')
