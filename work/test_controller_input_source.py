"""The real input mutation path must preserve keyboard and mixed input."""
from pathlib import Path
from lupa import LuaRuntime
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute('''
runtime={permits=function()return permitted~=false end}
dofile=function()return runtime end
dmc5_switch_controller={hooked=true,enabled=true,oldShoulders=0,blocked=0}
''')
lua.globals().C=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_controller.lua').read_text())
lua.execute('''
local function enumField(name,value)
 return {get_name=function()return name end,get_data=function()return value end}
end
sdk={get_managed_singleton=function()return {call=function()return paused or false end}end,
 find_type_definition=function(name)
  assert(name=='app.PadInput.GameAction')
  if missingMetadata then return nil end
  return {get_fields=function()return {enumField('Attack',0),enumField('Provocation',3),
   enumField('LockOn',4),enumField('None',4294967295),enumField('Max',32)}end}
 end}
mapping={get_size=function()return 5 end,read_dword=function(_,offset)
 local index=(offset-0x20)//4
 if index==3 then return 16 elseif index==4 then return 1024 else return 0 end
end}
pad={values={},keyboard={},writes=0,call=function(self,name,value)
 if name=='get_padButton'then return self.raw or 0 end
 if name=='get_keyAssignArray'then return mapping end
 if name=='isKeyboardDown'then
  if brokenSource then error('source unavailable')end
  assert(value==0 or value==3 or value==4,'invalid enum value queried')
  return self.keyboard[value]==true
 end
 if name:sub(1,4)=='get_'then return self.values[name:sub(5)]or 0 end
 assert(name:sub(1,4)=='set_');self.writes=self.writes+1;self.values[name:sub(5)]=value
end}
player={call=function(_,name)assert(name=='get_padInput');return pad end}
C.manager={call=function(_,name)assert(name=='get_manualPlayer');return player end}
function input(raw,keyboard)
 pad.raw=raw;pad.keyboard=keyboard or {};pad.writes=0
 for _,name in ipairs({'buttonOnFlags','buttonTriggerFlags','maskedTriggerFlags','buttonReleaseFlags','oldButtonOnFlags'})do pad.values[name]=24 end
 for _,name in ipairs({'padButton','padButtonDown','padButtonUp'})do pad.values[name]=raw end
 C.process(pad)
end
function untouched()
 assert(pad.writes==0 and pad.values.buttonOnFlags==24 and C.pending==nil,'normal input mutated or triggered switching')
end
for _,sequence in ipairs({{1024,1040,1024,0},{16,1040,16,0},{1040,0}})do
 C.reset();C.pad=nil
 for _,raw in ipairs(sequence)do input(raw,{[3]=true,[4]=true});untouched()end
end
C.reset();C.pad=nil;input(0);input(1024);input(1040);untouched();input(1024);untouched()
C.reset();C.pad=nil;input(0);input(16);input(1040)
assert(C.pending==1 and pad.writes>0 and pad.values.buttonOnFlags==0)
input(1040,{[3]=true});untouched()
C.reset();C.pad=nil;input(0);input(16)
brokenSource=true;input(1040);untouched();assert(C.error:find('source unavailable'));brokenSource=false
C.keyboardActions=nil;missingMetadata=true;input(1040);untouched();assert(C.error);missingMetadata=false
C.reset();C.pad=nil;input(0);input(16);paused=true;input(1040);untouched();paused=false
''')
print('PASS: keyboard Shift/taunt equivalents in either order and mixed input cause zero writes; lock-first preserved; controller modifier-first switching, invalid metadata, source failure and pause guards covered')
