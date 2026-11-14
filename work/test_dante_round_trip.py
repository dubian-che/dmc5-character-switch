"""Exercise real progression module against the observed missing S01 lifecycle."""
from pathlib import Path
from lupa import LuaRuntime
from lua_test_support import install_module_loader

l=LuaRuntime();install_module_loader(l)
l.execute('''
local names={'app.ChargeParameter','app.PadInput','System.UInt32','System.Int32','System.Int32'}
local params={};for i,n in ipairs(names)do params[i]={get_full_name=function()return n end}end
local method={get_name=function()return 'setData'end,get_param_types=function()return params end,
 call=function(_,c,p,input,flag,start,limit)
  assert(flag==4096 and start==0 and limit==2147483647)
  c.writes=c.writes+1;if c.fail then error('native failure')end
  c.parameter=p;c.input=input;c.flag=flag;c.timer=0
 end}
sdk={hook=function()end,find_type_definition=function()return {
 get_method=function(_,n)return n end,get_methods=function()return {method}end}end}
function actor(id,level,weapon)
 local a={id=id,level=level,weapon=weapon,input={},parameter={},setups=0,sheath={timer=123}}
 local c={writes=0,flag=0,timer=0};a.charge=c
 function c:call(n)
  if n=='get_parameter'then return self.parameter
  elseif n=='get_padInput'then return self.input
  elseif n=='get_padInputFlag'then return self.flag
  else error(n)end
 end
 local style={get_field=function(_,n)assert(n=='Level');return a.level end}
 local data={get_field=function(_,n)assert(n=='SwordMaster');return style end}
 local skills={get_field=function(_,n)assert(n=='DS_RoundTrip');return a.parameter end}
 local characteristic={get_field=function(_,n)assert(n=='ChargeSkill');return skills end}
 function a:get_field(n)
  if n=='IsEnemyDante'then return self.enemy
  elseif n=='<chargeWeaponS01>k__BackingField'then return self.charge
  elseif n=='CharacteristicParameter'then return characteristic
  else error('must not touch other channels: '..n)end
 end
 function a:call(n)
  if n=='get_playerID'then return self.id
  elseif n=='get_currentWeaponS'then return self.weapon
  elseif n=='get_playerData'then return data
  elseif n=='get_padInput'then return self.input
  elseif n=='setupChargeWeaponS01'then self.setups=self.setups+1;self.callbacks={native=true}
  else error('unexpected actor mutation '..n)end
 end
 return a
end
''')
l.globals().P=l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_progression.lua').read_text())
l.execute('''
local p=actor(1,1,2);assert(not P.refreshDanteRoundTrip(p))
p.level=4;assert(P.refreshDanteRoundTrip(p))
assert(p.charge.parameter==p.parameter and p.charge.input==p.input and p.setups==1)
local callbacks=p.callbacks;p.charge.timer=4.5
for i=1,1000 do assert(not P.refreshDanteRoundTrip(p))end
assert(p.charge.timer==4.5 and p.callbacks==callbacks and p.charge.writes==1)
assert(p.sheath.timer==123 and p.weapon==2)
local replacement=actor(1,2,2);assert(P.refreshDanteRoundTrip(replacement))
for _,id in ipairs({0,2,4})do assert(not P.refreshDanteRoundTrip(actor(id,4,2)))end
for _,wp in ipairs({0,1,3,4,5,6})do assert(not P.refreshDanteRoundTrip(actor(1,4,wp)))end
local enemy=actor(1,4,2);enemy.enemy=true;assert(not P.refreshDanteRoundTrip(enemy))
local absent=actor(1,4,2);absent.parameter=nil;assert(not P.refreshDanteRoundTrip(absent))
absent=actor(1,4,2);absent.input=nil;assert(not P.refreshDanteRoundTrip(absent))
local partial=actor(1,4,2);partial.charge.flag=4096;assert(not P.refreshDanteRoundTrip(partial))
partial=actor(1,4,2);partial.charge.input={};assert(not P.refreshDanteRoundTrip(partial))
local failed=actor(1,4,2);failed.charge.fail=true;assert(not pcall(P.refreshDanteRoundTrip,failed))
for i=1,1000 do assert(not P.refreshDanteRoundTrip(failed))end
assert(failed.charge.writes==1 and failed.setups==0)
''')
print('PASS: DSD missing style-charge initialization, native arguments/callbacks, held charge and sheath preservation, actor replacement, weapon/style/identity guards, bounded failure.')
