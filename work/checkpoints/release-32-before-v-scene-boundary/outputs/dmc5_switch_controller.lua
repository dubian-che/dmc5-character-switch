-- Controller modifier: configured taunt + LB previous / RB next.
local C=_G.dmc5_switch_controller or {enabled=true,oldShoulders=0,blocked=0}
_G.dmc5_switch_controller=C
C.LB=256;C.RB=1024;C.shoulders=C.LB|C.RB
function C.evaluate(raw,modifier,allowed)
 local held=raw&C.shoulders
 local pressed=held&(~C.oldShoulders);C.oldShoulders=held
 if not allowed then C.blocked=0;C.comboHeld=false;return nil,0,false end
 C.blocked=C.blocked&held
 local direction
 if modifier and held~=0 then
  C.blocked=C.blocked|held;C.comboHeld=true
  if held==C.LB and pressed&C.LB~=0 then direction=-1
  elseif held==C.RB and pressed&C.RB~=0 then direction=1 end
 end
 local suppressTaunt=C.comboHeld and modifier
 if not modifier then C.comboHeld=false end
 return direction,C.blocked,suppressTaunt
end
function C.process(pad)
 local manager=C.manager;if not manager then return end
 local player=manager:call('get_manualPlayer')
 if not player or player:call('get_padInput')~=pad then return end
 local raw=pad:call('get_padButton')
 local mapping=pad:call('get_keyAssignArray');if not mapping or mapping:get_size()<4 then return end
 -- TDB67 enum-array elements are uint32 at the verified SystemArray data offset.
 local taunt=mapping:read_dword(0x20+3*4)
 local modifier=taunt~=0 and (raw&taunt)~=0
 local gm=sdk.get_managed_singleton('app.GameManager')
 local allowed=C.enabled and gm and not gm:call('get_isPause') and not gm:call('get_isPauseMenu') and not gm:call('get_isShopPause')
 local direction,blocked,suppressTaunt=C.evaluate(raw,modifier,allowed)
 if blocked~=0 or suppressTaunt then
  local mask=suppressTaunt and 8 or 0
  for i=0,math.min(mapping:get_size(),32)-1 do
   if (mapping:read_dword(0x20+i*4)&blocked)~=0 then mask=mask|(1<<i)end
  end
  for _,property in ipairs({'buttonOnFlags','buttonTriggerFlags','maskedTriggerFlags','buttonReleaseFlags','oldButtonOnFlags'})do
   pad:call('set_'..property,pad:call('get_'..property)&(~mask))
  end
  for _,property in ipairs({'padButton','padButtonDown','padButtonUp'})do
   pad:call('set_'..property,pad:call('get_'..property)&(~blocked))
  end
 end
 if direction then C.pending=direction end
 C.error=nil
end
if not C.hooked then
 sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
  C.manager=sdk.to_managed_object(args[2])
  if C.pending then
   local direction=C.pending;C.pending=nil
   local S=_G.dmc5_live_switch
   if S and S.step then S.step(direction)end
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
