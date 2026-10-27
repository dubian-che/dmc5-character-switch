-- Full move progression and normal maximum capacities, runtime only.
if _G.dmc5_switch_progression then return _G.dmc5_switch_progression end
local P={version=3,status={}}
_G.dmc5_switch_progression=P
local runtime=dofile('reframework/data/dmc5_switch_runtime.lua')
local seen={}
local bikeIDs
local neroChargeDataMethod,neroChargeAttempt
function P.refreshNeroCharge(player)
 if player:call('get_playerID')~=0 then return false end
 local data=player:call('get_playerData')
 local charge=player:get_field('BlueRoseCharge')
 if not data or not charge then return false end
 local level=data:get_field('ChargeShotLevel')
 if type(level)~='number'or level<0 or level>3 then return false end
 -- PlayerNero.initBlueRoseCharge passes ChargeShotLevel + 2 to setData.
 -- allOpen changes the skill but does not rebuild this cached runtime limit.
 local limit=level+2
 local current=charge:get_field('LimitLevel')
 if type(current)~='number'then return false end
 if current==limit then return false end
 local parameter=charge:call('get_parameter')
 local input=player:call('get_padInput')
 if not parameter or not input then return false end
 local previous=neroChargeAttempt
 if previous and previous.charge==charge and previous.parameter==parameter and
  previous.limit==limit and previous.result==current then return false end
 -- Resolve the native five-argument overload, preserving registered charge
 -- handlers. initBlueRoseCharge/resetData would replace those handlers.
 if not neroChargeDataMethod then
  local t=sdk.find_type_definition('app.ChargeChecker')
  local expected={'app.ChargeParameter','app.PadInput','System.UInt32','System.Int32','System.Int32'}
  for _,method in ipairs(t:get_methods())do
   if method:get_name()=='setData'then
    local params=method:get_param_types();local matches=#params==#expected
    if matches then for i,name in ipairs(expected)do if params[i]:get_full_name()~=name then matches=false;break end end end
    if matches then neroChargeDataMethod=method;break end
   end
  end
  assert(neroChargeDataMethod,'Nero charge setData overload unavailable')
 end
 neroChargeAttempt={charge=charge,parameter=parameter,limit=limit,result=current}
 charge:call('forceEnd')
 neroChargeDataMethod:call(charge,parameter,input,charge:call('get_padInputFlag'),charge:get_field('StartLevel'),limit)
 neroChargeAttempt.result=charge:get_field('LimitLevel')
 assert(neroChargeAttempt.result==limit,'Nero charge limit did not refresh')
 P.neroChargeRepairs=(P.neroChargeRepairs or 0)+1;P.neroChargeWarning=nil
 return true
end
local function enumValue(typeName,name)
 local t=sdk.find_type_definition(typeName)
 local f=t and t:get_field(name)
 local value=f and f:get_data(nil)
 assert(type(value)=='number','Weapon enum unavailable: '..typeName..'.'..name)
 return value
end
local function bikeReady(player)
 if player:call('get_playerID')~=1 or player:get_field('IsEnemyDante')then return false end
 if not bikeIDs then
  bikeIDs={normal=enumValue('app.PlayerDante.WeaponS','Emperor'),red=enumValue('app.PlayerDante.WeaponS','EmperorRB'),
   left=enumValue('app.PlayerDante.Weapon','EmperorRBL'),right=enumValue('app.PlayerDante.Weapon','EmperorRBR')}
 end
 -- Only select the real red-bike weapon when its native components exist.
 -- Do not forge DLC availability or substitute a model for an absent weapon.
 local container=player:call('get_weaponContainer')
 if not container or not container:call('ContainsKey',bikeIDs.left)or not container:call('ContainsKey',bikeIDs.right)then
  P.redBikeWarning='Cavaliere R weapon components are not loaded';return false
 end
 P.redBikeWarning=nil;return true
end
function P.redBikeWeapon(player,weapon)
 if not bikeReady(player)then return weapon end
 return weapon==bikeIDs.normal and bikeIDs.red or weapon
end
function P.lockRedBike(player)
 if not bikeReady(player)then return false end
 local slots=player:call('get_slotWeaponS')
 if slots then
  for i=0,slots:call('get_Count')-1 do
   if slots:call('get_Item',i)==bikeIDs.normal then slots:call('set_Item',i,bikeIDs.red)end
  end
 end
 if player:call('get_currentWeaponS')==bikeIDs.normal then
  player:call('changeWeaponS',bikeIDs.red,player:call('get_weaponS_ID'))
 end
 return true
end
function P.apply(player)
 local id=player:call('get_playerID')
 if id~=0 and id~=1 and id~=4 then return end
 local data=player:call('get_playerData');if not data then return end
 local identity=tostring(player:get_address())..':'..tostring(data:get_address())
 local first=seen[id]~=identity
 local oldHpMax=player:call('get_maxHp')
 local oldDtMax=player:call('get_maxDevilTriggerGauge')
 local oldHp=player:call('get_hp');local oldDt=player:call('get_devilTriggerGauge')
 -- Use each concrete character's own allOpen; Vergil retains native jump rules.
 local super=data:get_field('IsSuperMode')
 data:call('allOpen');data:set_field('IsSuperMode',super)
 if id==0 then
  local ok,why=pcall(P.refreshNeroCharge,player)
  if not ok then P.neroChargeWarning=tostring(why)end
 end
 -- Native allOpen omits Dr. Faust's purchase level; enum Lv4 is 3.
 if id==1 then
  data:get_field('FaustHat'):set_field('Gambling',3)
  local ok,why=pcall(P.lockRedBike,player)
  if not ok then P.redBikeWarning=tostring(why)end
 end
 local maxHp=data:get_field('MaxHP')*1000.0
 local maxDt=data:get_field('MaxDT')*1000.0
 player:call('set_maxHp',maxHp)
 player:call('set_maxDevilTriggerGauge',maxDt)
 -- Fill once at initialization. Later handoffs preserve spent HP/DT.
 local palace=_G.dmc5_switch_palace
 local pending=palace and palace.pendingVitals(id)
 if first and not pending then
  player:call('set_hp',maxHp);player:call('set_devilTriggerGauge',maxDt)
 elseif not first then
  if oldHpMax~=maxHp then player:call('set_hp',math.min(maxHp,oldHp+math.max(0,maxHp-oldHpMax)))end
  if oldDtMax~=maxDt then player:call('set_devilTriggerGauge',math.min(maxDt,oldDt+math.max(0,maxDt-oldDtMax)))end
 end
 seen[id]=identity
 P.status[tostring(id)]={maxHp=player:call('get_maxHp'),maxDt=player:call('get_maxDevilTriggerGauge'),allSkills=true}
end
-- Rewrite only normal-bike selections. Other weapons, slots and native
-- animations keep their original flow; no per-frame equipment enforcement.
local hookOk,hookWhy=pcall(function()
 local t=sdk.find_type_definition('app.PlayerDante')
 local method=t and t:get_method('changeWeaponS')
 assert(method,'Dante weapon selection method unavailable')
 sdk.hook(method,function(args)
  local ok,why=pcall(function()
   if not runtime.permits()then return end
   local player=sdk.to_managed_object(args[2])
   local weapon=sdk.to_int64(args[3])
   local replacement=P.redBikeWeapon(player,weapon)
   if replacement~=weapon then args[3]=sdk.to_ptr(replacement)end
  end)
  if not ok then P.redBikeWarning=tostring(why)end
 end,function(ret)return ret end)
end)
if not hookOk then P.redBikeWarning=tostring(hookWhy)end
local ticks=0
sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)
 ticks=ticks+1;if ticks%120~=0 then return end
 local ok,why=pcall(function()
  local manager=sdk.to_managed_object(args[2])
  if not runtime.permits(manager)then return end
  for _,id in ipairs({0,1,4})do
   local p=manager:call('getPlayerByID',id)
   if p then
    local d=p:call('get_playerData')
    if d then
     local identity=tostring(p:get_address())..':'..tostring(d:get_address())
     if seen[id]~=identity or d:get_field('MaxHP')~=20 or d:get_field('MaxDT')~=10 then P.apply(p)end
     if id==0 then
      local ok,why=pcall(P.refreshNeroCharge,p)
      if not ok then P.neroChargeWarning=tostring(why)end
     end
    end
   end
  end
 end)
 if not ok then P.error=tostring(why)end
end,function(ret)return ret end)
return P

