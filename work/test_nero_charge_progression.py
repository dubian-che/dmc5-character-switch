"""A skill unlock must refresh the cached Blue Rose limit without polling resets."""
from pathlib import Path
from lupa import LuaRuntime
from lua_test_support import install_module_loader

l = LuaRuntime()
install_module_loader(l)
l.execute('''
local types={'app.ChargeParameter','app.PadInput','System.UInt32','System.Int32','System.Int32'}
local parameters={}
for i,name in ipairs(types)do parameters[i]={get_full_name=function()return name end}end
local wrong={get_name=function()return 'setData'end,get_param_types=function()return {1,2,3}end,
 call=function()error('wrong overload')end}
local correct={get_name=function()return 'setData'end,get_param_types=function()return parameters end,
 call=function(_,charge,param,input,flag,start,limit)
  assert(param==charge.parameter and flag==2 and start==0)
  assert(input==charge.owner.input,'native refresh kept stale input')
  charge.updates=charge.updates+1
  if charge.fail then error('native setData failure')end
  charge.LimitLevel=limit;charge.input=input;charge.timer=0
 end}
sdk={hook=function()end,find_type_definition=function(name)
 return {get_method=function(_,name)return name end,get_methods=function()return {wrong,correct}end}
end}
function actor(id,skill,limit)
 local p={id=id,skill=skill,input={},shells=4,hp=8000,dt=3000}
 local d={get_field=function(_,name)assert(name=='ChargeShotLevel');return p.skill end}
 local c={owner=p,LimitLevel=limit,StartLevel=0,parameter={},updates=0,resets=0,timer=160,handlers={token=true}}
 function c:get_field(name)return self[name]end
 function c:call(name)
  if name=='get_parameter'then return self.parameter
  elseif name=='get_padInputFlag'then return 2
  elseif name=='forceEnd'then self.resets=self.resets+1
  else error('unexpected charge mutation '..name)end
 end
 p.charge=c
 function p:get_field(name)assert(name=='BlueRoseCharge');return self.charge end
 function p:call(name)
  if name=='get_playerID'then return self.id
  elseif name=='get_playerData'then return d
  elseif name=='get_padInput'then return self.input
  else error(name)end
 end
 return p
end
''')
l.globals().P = l.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_progression.lua').read_text())
l.execute('''
-- Recorded failure: ChargeShotLevel=3 but cached LimitLevel=2.
local p=actor(0,3,2)
assert(P.refreshNeroCharge(p)and p.charge.LimitLevel==5)
assert(p.charge.input==p.input and p.charge.updates==1 and p.charge.resets==1)
assert(p.charge.handlers.token and p.shells==4 and p.hp==8000 and p.dt==3000)
p.charge.timer=240
for i=1,1000 do assert(not P.refreshNeroCharge(p))end
assert(p.charge.updates==1 and p.charge.resets==1 and p.charge.timer==240)
-- Native floor initialization may reuse the same object but reset its cap.
p.charge.LimitLevel=2;assert(P.refreshNeroCharge(p));assert(p.charge.LimitLevel==5)
for skill=0,3 do
 local other=actor(0,skill,-1)
 assert(P.refreshNeroCharge(other)and other.charge.LimitLevel==skill+2)
end
for _,id in ipairs({1,2,4})do
 local other=actor(id,3,2)
 assert(not P.refreshNeroCharge(other)and other.charge.updates==0)
end
local absent=actor(0,3,2);absent.charge=nil;assert(not P.refreshNeroCharge(absent))
local partial=actor(0,3,2);partial.charge.fail=true
assert(not pcall(P.refreshNeroCharge,partial))
for i=1,1000 do assert(not P.refreshNeroCharge(partial))end
assert(partial.charge.resets==1 and partial.charge.updates==1,'native failure repeatedly cancels charging')
''')
print('PASS: native five-argument limit refresh follows skill + 2; full charge is preserved over 1000 checks; scene cap resets, callbacks/ammo, other actors and partial failures covered.')
