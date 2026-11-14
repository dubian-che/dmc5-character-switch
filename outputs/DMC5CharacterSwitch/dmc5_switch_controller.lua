-- Controller modifier: native configured taunt plus a customizable physical button.
local C=_G.dmc5_switch_controller or {enabled=true,oldShoulders=0,blocked=0}
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
_G.dmc5_switch_controller=C
C.LB=256;C.RB=1024;C.shoulders=C.LB|C.RB
C.bindings={{mask=C.LB,action=-1},{mask=C.RB,action=1}}
local buttonFields={A='RDown',B='RRight',X='RLeft',Y='RUp',LB='LTrigTop',LT='LTrigBottom',RB='RTrigTop',RT='RTrigBottom'}
function C.configure(config)
 local definitions={{'padPrevious','LB',-1},{'padNext','RB',1},{'padNero','None','nero'},{'padDante','None','dante'},{'padVergil','None','vergil'}}
 local t=sdk.find_type_definition('via.hid.GamePadButton')
 local bindings,all,used={},0,{}
 for _,item in ipairs(definitions)do
  local name=config[item[1]]or item[2]
  if name~='None'then
   local field=t and buttonFields[name]and t:get_field(buttonFields[name])
   local mask=field and field:get_data(nil)
   assert(type(mask)=='number'and mask>0 and mask%1==0 and(mask&(mask-1))==0,'Controller button metadata unavailable: '..tostring(name))
   assert(not used[mask],'Duplicate controller button: '..name)
   used[mask]=true;all=all|mask;bindings[#bindings+1]={mask=mask,action=item[3]}
  end
 end
 C.bindings=bindings;C.shoulders=all;C.reset()
end
function C.reset(raw,modifier)
 C.oldShoulders=(raw or 0)&C.shoulders;C.oldModifier=modifier==true
 C.blocked=0;C.comboHeld=false;C.pending=nil
 C.lastMask=0;C.inputSource=nil
end
function C.evaluate(raw,modifier,allowed)
 local held=raw&C.shoulders
 local pressed=held&(~C.oldShoulders);C.oldShoulders=held
 local armed=C.oldModifier;C.oldModifier=modifier==true
 if not allowed then C.blocked=0;C.comboHeld=false;return nil,0,false end
 local released=C.blocked&(~held)
 C.blocked=C.blocked&held
 local direction
 -- Modifier first; one fresh secondary edge; multiple held bindings cancel.
 if modifier and armed and held~=0 and(held&(held-1))==0 then
  for _,binding in ipairs(C.bindings)do
   if held==binding.mask and(pressed&binding.mask)~=0 then direction=binding.action;break end
  end
  if direction then C.blocked=C.blocked|held;C.comboHeld=true end
 end
 local suppressTaunt=C.comboHeld and modifier
 if not modifier then C.comboHeld=false end
 return direction,C.blocked|released,suppressTaunt
end
local function keyboardActive(pad)
 -- PadInput is shared by keyboard and controller input. Query the native
 -- keyboard path using reflected enum values, never guessed key bindings.
 if not C.keyboardActions then
  local t=sdk.find_type_definition('app.PadInput.GameAction')
  assert(t,'Keyboard action metadata unavailable; controller chord disabled')
  local values,seen={},{}
  for _,f in ipairs(t:get_fields())do
   local name=f:get_name():lower()
   if name~='value__'and not name:find('max',1,true)and not name:find('count',1,true)and name~='none'and not name:find('num',1,true)then
    local ok,v=pcall(function()return f:get_data(nil)end)
    if ok and type(v)=='number'and v>=0 and v<32 and v%1==0 and not seen[v]then values[#values+1]=v;seen[v]=true end
   end
  end
  assert(#values>0,'Keyboard action values unavailable; controller chord disabled')
  C.keyboardActions=values
 end
 for _,id in ipairs(C.keyboardActions)do
  local value=pad:call('isKeyboardDown',id)
  assert(type(value)=='boolean','Keyboard source query unavailable; controller chord disabled')
  if value then return true end
 end
 return false
end
function C.process(pad)
 local manager=C.manager;if not manager then return end
 if not runtime.permits(manager)then C.reset();return end
 local player=manager:call('get_manualPlayer')
 if not player or player:call('get_padInput')~=pad then return end
 C.lastMask=0;C.inputSource=nil
 local raw=pad:call('get_padButton')
 local mapping=pad:call('get_keyAssignArray');if not mapping or mapping:get_size()<4 then return end
 -- TDB67 enum-array elements are uint32 at the verified SystemArray data offset.
 local taunt=mapping:read_dword(0x20+3*4)
 local modifier=taunt~=0 and (raw&taunt)~=0
 if C.pad~=pad then C.reset(raw,modifier);C.pad=pad end
 if (modifier and raw&C.shoulders~=0)or C.blocked~=0 or C.comboHeld then
  local ok,keyboard=pcall(keyboardActive,pad)
  if not ok or keyboard then
   C.reset(raw,modifier);C.error=not ok and tostring(keyboard)or nil
   C.inputSource=ok and 'keyboard' or 'unknown'
   return -- Keyboard/mixed/unknown input is never consumed by controller chords.
  end
  C.inputSource='controller'
 end
 local gm=sdk.get_managed_singleton('app.GameManager')
 local allowed=C.enabled and gm and not gm:call('get_isPause') and not gm:call('get_isPauseMenu') and not gm:call('get_isShopPause')
 -- A taunt button reassigned onto a selected secondary must remain ordinary input.
 if (taunt&C.shoulders)~=0 then C.reset(raw,modifier);C.error='Taunt overlaps a switching button';return end
 local direction,blocked,suppressTaunt=C.evaluate(raw,modifier,allowed)
 if blocked~=0 or suppressTaunt then
  local mask=suppressTaunt and 8 or 0
  for i=0,math.min(mapping:get_size(),32)-1 do
   if (mapping:read_dword(0x20+i*4)&blocked)~=0 then mask=mask|(1<<i)end
  end
  for _,property in ipairs({'buttonOnFlags','buttonTriggerFlags','maskedTriggerFlags','buttonReleaseFlags','oldButtonOnFlags'})do
   pad:call('set_'..property,pad:call('get_'..property)&(~mask))
  end
  C.lastMask=mask
  for _,property in ipairs({'padButton','padButtonDown','padButtonUp'})do
   pad:call('set_'..property,pad:call('get_'..property)&(~blocked))
  end
 end
 if direction then C.pending=direction end
 C.error=nil
end
local switch=_G.dmc5_live_switch
if switch and switch.config then
 local ok,why=pcall(C.configure,switch.config)
 if not ok then C.enabled=false;C.error=tostring(why)end
end
if not C.hooked then
 sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
  C.manager=sdk.to_managed_object(args[2])
  if not runtime.permits(C.manager)then C.reset();return end
  if C.pending then
   local direction=C.pending;C.pending=nil
   local S=_G.dmc5_live_switch
   if S then
    if type(direction)=='number'then if S.step then S.step(direction)end
    elseif S.request then
     local target=({nero=0,dante=1,vergil=4})[direction]
     if target and(S.current==0 or S.current==1 or S.current==4)then
      if S.requestDirect then S.requestDirect(target)
      elseif target~=S.current then S.request(target)end
     end
    end
   end
  end
 end,function(ret)return ret end)
 sdk.hook(sdk.find_type_definition('app.PadInput'):get_method('update'),function(args)
  thread.get_hook_storage().dmc5_combo_pad=sdk.to_managed_object(args[2])
 end,function(ret)
  local pad=thread.get_hook_storage().dmc5_combo_pad
  local ok,why=pcall(C.process,pad)
  if not ok then C.error=tostring(why)end
  return ret
 end)
 C.hooked=true
end
return C
