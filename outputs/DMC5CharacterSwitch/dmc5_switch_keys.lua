-- Configurable cycling and direct character selection.
local K={sequence={0,1,4}}
local padDefaults={padPrevious='LB',padNext='RB',padNero='None',padDante='None',padVergil='None'}
local padValid={None=true,A=true,B=true,X=true,Y=true,LB=true,LT=true,RB=true,RT=true}
function K.valid_key(key)
 if type(key)~='number' or key%1~=0 then return false end
 return key==8 or key==9 or key==13 or key==19 or key==20 or
  (key>=32 and key<=40) or key==46 or (key>=48 and key<=57) or
  (key>=65 and key<=90) or (key>=96 and key<=111) or (key>=112 and key<=135) or
  key==144 or key==145 or (key>=186 and key<=192) or (key>=219 and key<=222)
end
function K.defaults()
 local config={version=1,nextKey=0x80,previousKey=0x81,controllerCombo=true,neroKey=118,danteKey=119,vergilKey=120}
 for name,value in pairs(padDefaults)do config[name]=value end
 return config
end
function K.load_config()
 local config=K.defaults()
 local ok,data=pcall(function()return json.load_file('dmc5_switch_config.json')end)
 if not ok then return config,'Cannot read key configuration; using F17/F18.'end
 if data==nil then return config end
 if type(data)~='table' or (data.version~=nil and data.version~=1)then return config,'Unsupported key configuration; using defaults.'end
 local nextKey=data.nextKey
 local previousKey=data.previousKey
 if nextKey==nil then nextKey=config.nextKey end
 if previousKey==nil then previousKey=config.previousKey end
 if not K.valid_key(nextKey) or not K.valid_key(previousKey) or nextKey==previousKey then
  return config,'Invalid or duplicate switching keys; using F17/F18.'
 end
 if data.controllerCombo~=nil and type(data.controllerCombo)~='boolean'then return config,'Invalid controller option; using defaults.'end
 local used={[nextKey]=true,[previousKey]=true}
 for _,name in ipairs({'neroKey','danteKey','vergilKey'})do
  local key=data[name]
  if key==nil then key=used[config[name]]and 0 or config[name]end
  if key~=0 and(not K.valid_key(key)or used[key])then return K.defaults(),'Invalid or duplicate switching keys; using defaults.'end
  config[name]=key;if key~=0 then used[key]=true end
 end
 local padUsed={}
 for _,name in ipairs({'padPrevious','padNext','padNero','padDante','padVergil'})do
  local value=data[name];if value==nil then value=padDefaults[name]end
  if type(value)~='string'or not padValid[value]or(value~='None'and padUsed[value])then
   return K.defaults(),'Invalid or duplicate controller buttons; using defaults.'
  end
  config[name]=value;if value~='None'then padUsed[value]=true end
 end
 config.nextKey=nextKey;config.previousKey=previousKey
 if data.controllerCombo~=nil then config.controllerCombo=data.controllerCombo end
 return config
end
local actions={{'nextKey',1},{'previousKey',-1},{'neroKey',0},{'danteKey',1},{'vergilKey',4}}
function K.poll(S,state,config,is_down)
 local count,pressed,action=0,false,nil
 for i,item in ipairs(actions)do
  local key=config[item[1]]or 0
  local down=key~=0 and is_down(key)or false
  if down then count=count+1;pressed=not state[item[1]];action=i end
  state[item[1]]=down
 end
 -- Update every edge even for cancelled chords, so releasing one key cannot switch.
 if count~=1 or not pressed then return end
 S.keyPressCount=(S.keyPressCount or 0)+1
 if action<=2 then
  S.lastKeyDirection=actions[action][2];S.step(S.lastKeyDirection)
 else
  S.lastKeyDirection=0;S.lastKeyTarget=actions[action][2]
  if S.current==0 or S.current==1 or S.current==4 then
   if S.requestDirect then S.requestDirect(S.lastKeyTarget)
   elseif S.lastKeyTarget~=S.current then S.request(S.lastKeyTarget)end
  end
 end
end
-- One shared input source for switching and diagnostics. Never OR sources:
-- REFramework's window-message state may remain stuck after an external hook.
local input=_G.dmc5_switch_keyboard
if not input then
 input={source='unavailable',armed={},native=nil}
 _G.dmc5_switch_keyboard=input
 local ok,fn=pcall(function()
  if _VERSION~='Lua 5.4' then error('Keyboard module requires Lua 5.4')end
  local f,why=package.loadlib('reframework/data/dmc5_keyboard.dll','dmc5_keyboard_poll')
  assert(f,why);return f
 end)
 if ok then input.native=fn;input.source='windows-poll'
 else input.error=tostring(fn);if log and log.error then log.error('DMC5 keyboard unavailable: '..input.error)end end
end
function K.read_key(key)
 if not K.valid_key(key)then return false end
 if not input.native then return false end -- explicit failure, never stale RF keys
 local ok,focused,down=pcall(input.native,key)
 if not ok then input.error=tostring(focused);input.source='error';input.armed={};return false end
 if not focused then input.armed={};return false end
 if not down then input.armed[key]=true;return false end
 return input.armed[key]==true
end
K.input=input
function K.next_id(current,direction)
 local index=1
 for i,id in ipairs(K.sequence)do if id==current then index=i;break end end
 return K.sequence[(index-1+(direction<0 and -1 or 1))%#K.sequence+1]
end
function K.install(S)
 local dispatch=S.request
 function S.step(direction)
  if S.current~=0 and S.current~=1 and S.current~=4 then return end
  local current=S.getCycleID and S.getCycleID()or S.current
  local id=K.next_id(current,direction)
  dispatch(id)
 end
end
return K
