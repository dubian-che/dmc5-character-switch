"""Config and native enum-backed physical-button switching through real callbacks."""
from pathlib import Path
from lupa import LuaRuntime
lua=LuaRuntime(unpack_returned_tuples=True)
k=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_keys.lua').read_text())
lua.globals().K=k
lua.execute("""
json={load_file=function()return supplied end}
for _,bad in ipairs({{padNero='A',padDante='A'},{padNext='bad'},{padNext=false},{padPrevious=256}})do
 supplied=bad;local cfg,warning=K.load_config();assert(warning and cfg.padPrevious=='LB'and cfg.padNext=='RB'and cfg.padNero=='None')
end
supplied={padPrevious='LT',padNext='RT',padNero='A',padDante='X',padVergil='Y'}
local cfg,why=K.load_config();assert(not why and cfg.padPrevious=='LT'and cfg.padNext=='RT'and cfg.padNero=='A')
""")
lua.execute("""
runtime={permits=function()return true end};dofile=function()return runtime end
hooks={};thread={get_hook_storage=function()return {}end}
buttonMasks={RDown=32,RRight=128,RLeft=64,RUp=16,LTrigTop=256,LTrigBottom=512,RTrigTop=1024,RTrigBottom=2048}
sdk={to_managed_object=function(v)return v end,hook=function(method,pre,post)hooks[method]={pre,post}end,
 find_type_definition=function(name)
  return {get_method=function(_,method)return name..'.'..method end,
   get_field=function(_,field)assert(name=='via.hid.GamePadButton');return {get_data=function()return buttonMasks[field]end}end,
   get_fields=function()return {{get_name=function()return 'Attack'end,get_data=function()return 0 end}}end}
 end,
 get_managed_singleton=function()return {call=function()return false end}end}
""")
c=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_controller.lua').read_text());lua.globals().C=c
lua.execute("""
local expected={A=32,B=128,X=64,Y=16,LB=256,LT=512,RB=1024,RT=2048}
for name,mask in pairs(expected)do
 C.configure({padPrevious='None',padNext='None',padNero=name,padDante='None',padVergil='None'})
 assert(C.evaluate(0,true,true)==nil)
 local action,blocked,suppress=C.evaluate(mask,true,true)
 assert(action=='nero'and blocked==mask and suppress,'custom physical key not claimed: '..name)
 assert(C.evaluate(mask,true,true)==nil,'held button repeated')
 assert(select(2,C.evaluate(mask,false,true))==mask,'release leaked')
 C.reset();assert(C.evaluate(mask,true,true)==nil,'simultaneous modifier/button consumed')
end
C.configure({padPrevious='LT',padNext='RT',padNero='A',padDante='X',padVergil='Y'})
C.evaluate(0,true,true);assert(C.evaluate(512,true,true)==-1)
C.evaluate(0,true,true);assert(C.evaluate(2048,true,true)==1)
C.evaluate(0,true,true);assert(C.evaluate(32|64,true,true)==nil,'multiple targets not cancelled')
assert(C.evaluate(32,true,true)==nil,'chord release selects actor')
local count=0
local S={current=0,request=function(id)count=count+1;lastTarget=id end,step=function(v)lastDirection=v end}
dmc5_live_switch=S
C.pending='vergil';hooks['app.PlayerManager.doUpdate'][1]({[2]={}});assert(lastTarget==4 and count==1 and not C.pending)
C.pending='nero';hooks['app.PlayerManager.doUpdate'][1]({[2]={}});assert(count==1,'same actor switched')
S.requestDirect=function(id)count=count+1;lastTarget=id end
C.pending='nero';hooks['app.PlayerManager.doUpdate'][1]({[2]={}});assert(lastTarget==0 and count==2,'same actor did not reach shared direct-selection handler')
C.pending=-1;hooks['app.PlayerManager.doUpdate'][1]({[2]={}});assert(lastDirection==-1)
-- Native input flags must suppress claimed LT/RT/face actions, preserving unrelated bits.
mapping={get_size=function()return 6 end,read_dword=function(_,off)return ({32,512,2048,16384,64,16})[(off-0x20)//4+1]end}
pad={values={},call=function(self,name,value)
 if name=='get_keyAssignArray'then return mapping end
 if name=='get_padButton'then return raw end
 if name=='isKeyboardDown'then return keyboard or false end
 if name:sub(1,4)=='get_'then return self.values[name:sub(5)]or 0 end
 self.values[name:sub(5)]=value
end}
local player={call=function()return pad end};C.manager={call=function()return player end}
local function input(v)
 raw=v
 for _,key in ipairs({'buttonOnFlags','buttonTriggerFlags','maskedTriggerFlags','buttonReleaseFlags','oldButtonOnFlags'})do pad.values[key]=63 end
 for _,key in ipairs({'padButton','padButtonDown','padButtonUp'})do pad.values[key]=v end
 C.process(pad)
end
for mask,action in pairs({[32]='nero',[64]='dante',[16]='vergil',[512]=-1,[2048]=1})do
 C.reset();C.pad=nil;input(0);input(16384);input(16384|mask)
 assert(C.pending==action and C.lastMask~=0)
 assert(pad.values.buttonOnFlags==(63&(~C.lastMask)))
 assert(pad.values.padButton==16384,'physical button not masked')
 input(16384)
 assert(C.lastMask~=0 and pad.values.buttonReleaseFlags==(63&(~C.lastMask)),'claimed release leaked to gameplay')
end
C.reset();C.pad=nil;input(0);input(16384);keyboard=true;input(16384|32)
assert(not C.pending and pad.values.buttonOnFlags==63,'mixed input consumed')
keyboard=false
local original=mapping.read_dword
mapping.read_dword=function(self,off)if off==0x20+3*4 then return 32 end;return original(self,off)end
C.reset();C.pad=nil;input(0);input(32);input(32|64)
assert(not C.pending and pad.values.buttonOnFlags==63 and C.error:find('Taunt overlaps'),'taunt overlap consumed input')
""")
print('PASS: all eight reflected physical buttons, LT/RT/face flag suppression, config validation, chords, repeats, direct request and pending replacement, keyboard isolation.')
