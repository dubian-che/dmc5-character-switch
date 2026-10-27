-- Native spoken taunts only; no taunt action or animation is started.
if _G.dmc5_switch_voice then return _G.dmc5_switch_voice end
local V={version=2,enabled=true,played=0,cooldownMs=3000,lastPlayed={},lastEvents={},pools={}}
_G.dmc5_switch_voice=V
V.events={
 [0]={
  'SND_AUTO_PL0000_V_PROVOCATION_SP_01',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_02',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_03',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_04',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_05',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_06',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_07',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_08',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_09',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_10',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_11',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_13',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_16',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_20',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_21',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_22',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_23',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_24',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_25',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_26',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_27',
  'SND_AUTO_PL0000_V_PROVOCATION_SP_28',
 },
 [1]={
  'SND_AUTO_PL0100_V_PROVOCATION_SP_01_01',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_02_01',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_03_01',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_05',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_06',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_07',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_08',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_09',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_10',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_11',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_12',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_20',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_21',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_22',
  'SND_AUTO_PL0100_V_PROVOCATION_SP_23',
 },
 [4]={
  'SND_AUTO_PL0800_V_PROVOCATION_SP_02',
  'SND_AUTO_PL0800_V_PROVOCATION_SP_03',
  'SND_AUTO_PL0800_V_PROVOCATION_SP_05',
  'SND_AUTO_PL0800_V_PROVOCATION_SP_06',
  'SND_AUTO_PL0800_V_PROVOCATION_SP_07',
  'SND_AUTO_PL0800_V_PROVOCATION_SP_08',
  'SND_AUTO_PL0800_V_PROVOCATION_SP_09',
  'SND_AUTO_PL0800_V_PROVOCATION_SP_10',
  'SND_AUTO_PL0800_V_PROVOCATION_SP_11',
 },
}
local function method(typeName,name,param)
 local t=sdk.find_type_definition(typeName);if not t then return nil end
 for _,m in ipairs(t:get_methods())do
  local ps=m:get_param_types()
  if m:get_name()==name and #ps==1 and ps[1]:get_full_name()==param then return m end
 end
end
local trigger=method('app.character.Character','triggerVoice','System.String')
local exists=method('via.wwise.WwiseContainer','exists','System.String')
local environment=sdk.find_type_definition('System.Environment')
local clock=environment and environment:get_method('get_TickCount')
local function loaded(container,candidates)
 local events={}
 for _,event in ipairs(candidates)do
  if exists:call(container,event)then events[#events+1]=event end
 end
 return events
end
function V.play(player)
 if not V.enabled then return false end
 local ok,result=pcall(function()
  local id=player:call('get_playerID');local candidates=V.events[id]
  if not candidates then return false end
  assert(clock and trigger and exists,'Voice interface unavailable')
  -- TickCount is monotonic milliseconds. Unsigned subtraction handles its
  -- signed transition and 49.7-day wrap without relying on frame/CPU time.
  local now=clock:call(nil)%4294967296
  local previous=V.lastPlayed[id]
  if previous and(now-previous)%4294967296<V.cooldownMs then return false end
  local container=player:call('get_GameObject'):call('getComponent',sdk.typeof('app.WwiseContainerApp'))
  if not container then return false end
  local pool=V.pools[id]
  if not pool or pool.container~=container then
   pool={container=container,events=loaded(container,candidates)};V.pools[id]=pool
  end
  -- Recheck cached availability: native banks may change on the same actor.
  local available={}
  for _,event in ipairs(pool.events)do
   if exists:call(container,event)then available[#available+1]=event end
  end
  if #available==0 then
   available=loaded(container,candidates);pool.events=available
  end
  if #available==0 then return false end
  local choices={}
  for _,event in ipairs(available)do
   if #available==1 or event~=V.lastEvents[id]then choices[#choices+1]=event end
  end
  local event=choices[math.random(#choices)]
  trigger:call(player,event)
  V.lastPlayed[id]=now;V.lastEvents[id]=event
  V.lastPlayer=id;V.lastEvent=event;V.played=V.played+1;V.error=nil
  return true
 end)
 if not ok then V.error=tostring(result);return false end
 return result
end
return V
