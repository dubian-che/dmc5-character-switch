"""Check all owner-input channels against independently extracted native metadata."""
import json
from pathlib import Path
from lupa import LuaRuntime
from lua_test_support import install_module_loader

# Only schema field names are retained; no live objects, addresses or captures.
native_fields = {int(k): v for k, v in json.loads(
    Path('work/fixtures/native-charge-fields.json').read_text(encoding='utf-8')).items()}

lua = LuaRuntime()
install_module_loader(lua)
lua.execute('''
sdk={hook=function()end,find_type_definition=function()return {get_method=function()end}end}
function checker(input,flag)
 local c={input=input,flag=flag,parameter={},Enable=true,LimitLevel=2147483647,timer=3.5,state=2,resets=0,ends=0,binds=0,callbacks={}}
 function c:get_address()return 100 end
 function c:get_field(n)
  if n=='Enable'then return self.Enable
  elseif n=='LimitLevel'then return self.LimitLevel
  elseif n=='<state>k__BackingField'then return self.state
  elseif n=='<currentLevel>k__BackingField'then return 1
  elseif n=='<timer>k__BackingField'then return self.timer else error(n)end
 end
 function c:call(n,a)
  if n=='get_padInput'then return self.input
  elseif n=='get_parameter'then return self.parameter
  elseif n=='get_padInputFlag'then return self.flag
  elseif n=='forceEnd'then self.ends=self.ends+1
  elseif n=='reset'then assert(a==false);self.resets=self.resets+1;self.state=0;self.timer=0
  elseif n=='set_padInput'then self.binds=self.binds+1;if self.fail then error('native bind rejected')end;self.input=a
  else error('Unexpected charge mutation '..n)end
 end
 return c
end
function actor(id,names)
 local p={id=id,input={},fields={},enabled=true,event=false,shotResets=0,effectEnds=0}
 for _,name in ipairs(names)do p.fields[name]=checker({},1)end
 function p:get_field(name)return self.fields[name]end
 function p:call(n)
  if n=='get_playerID'then return self.id
  elseif n=='get_Enable'then return self.enabled
  elseif (n=='get_isEventMove'or n=='get_isEventRun')then return self.event
  elseif n=='get_padInput'then return self.input
  elseif n=='resetGunShotReserve'then self.shotResets=self.shotResets+1
  elseif n=='finishBRChargeEffect'then self.effectEnds=self.effectEnds+1
  else error('Unexpected player mutation '..n)end
 end
 return p
end
''')
lua.globals().R = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_resources.lua').read_text())

for ident, names in native_fields.items():
    lua.globals().p = lua.globals().actor(ident, lua.table_from(names))
    lua.globals().names = lua.table_from(names)
    lua.execute('''
local callbacks={};local params={};local clone='<DoppelJudgeMentCutCharge>k__BackingField'
for name,c in pairs(p.fields)do callbacks[name]=c.callbacks;params[name]=c.parameter end
assert(R.bindPlayerChargeInputs(p))
for name,c in pairs(p.fields)do
 if name==clone then assert(c.input~=p.input and c.binds==0,'clone-owned input was rebound to the manual actor')
 else assert(c.input==p.input and c.binds==1 and c.resets==1)end
 assert(c.parameter==params[name]and c.callbacks==callbacks[name]and c.LimitLevel==2147483647)
 c.timer=7.25;c.state=3
end
for i=1,1000 do assert(not R.bindPlayerChargeInputs(p))end
for name,c in pairs(p.fields)do assert(c.timer==7.25 and c.state==3,'normal held charge was reset')end
if p.id==0 then assert(p.shotResets==1 and p.effectEnds==1)end
-- Replacing the input profile is a new binding epoch; initialized channels
-- follow it once, preserving parameter/limit/callback identity.
p.input={};assert(R.bindPlayerChargeInputs(p))
for name,c in pairs(p.fields)do if name~=clone then assert(c.input==p.input and c.binds==2)end end
''')

lua.globals().p = lua.globals().actor(1, lua.table_from(native_fields[1]))
lua.execute('''
local s=p.fields['<chargeWeaponS00>k__BackingField']
local style=p.fields['<chargeWeaponS01>k__BackingField']
style.flag=4096
local unused=p.fields['<chargeWeaponL00>k__BackingField'];unused.parameter=nil;unused.flag=0
local off=p.fields['<chargeWeaponL01>k__BackingField'];off.Enable=false
local valid=p.fields['<chargeSheath>k__BackingField'];valid.input=p.input
s.fail=true
assert(R.bindPlayerChargeInputs(p),'one failed channel prevented style repair')
assert(style.input==p.input and style.flag==4096 and valid.binds==0 and unused.binds==0 and off.binds==0)
for i=1,1000 do R.bindPlayerChargeInputs(p)end
assert(s.binds==1 and style.binds==1,'failed tuple or successful channel repeatedly retried')
s.fail=false;p.input={};assert(R.bindPlayerChargeInputs(p));assert(s.input==p.input and s.binds==2)
p.event=true;p.input={};local count=s.binds
assert(not R.bindPlayerChargeInputs(p)and s.binds==count)
p.event=false;p.enabled=false;assert(not R.bindPlayerChargeInputs(p)and s.binds==count)
''')
print('PASS: native Nero 4 / Dante 5 / playable Vergil 3 owner-input channels; clone-owned channel preserved; no reset of valid charge; input-profile replacement, uninitialized/disabled channels and bounded partial failures covered.')
lua.execute('assert(R.captureChargeInputs==nil)')
