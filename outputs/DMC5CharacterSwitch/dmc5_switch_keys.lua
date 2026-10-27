-- Bidirectional cycling. IDs are internal; player-facing controls are only previous/next.
local K={sequence={0,1,4}}
function K.valid_key(key)
 if type(key)~='number' or key%1~=0 then return false end
 return key==8 or key==9 or key==13 or key==19 or key==20 or
  (key>=32 and key<=40) or key==46 or (key>=48 and key<=57) or
  (key>=65 and key<=90) or (key>=96 and key<=111) or (key>=112 and key<=135) or
  key==144 or key==145 or (key>=186 and key<=192) or (key>=219 and key<=222)
end
function K.load_config()
 local config={version=1,nextKey=0x80,previousKey=0x81,controllerCombo=true}
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
 config.nextKey=nextKey;config.previousKey=previousKey
 if data.controllerCombo~=nil then config.controllerCombo=data.controllerCombo end
 return config
end
function K.poll(S,state,config,is_down)
 local nextDown=is_down(config.nextKey)
 local previousDown=is_down(config.previousKey)
 local nextPressed=nextDown and not state.nextDown
 local previousPressed=previousDown and not state.previousDown
 state.nextDown=nextDown;state.previousDown=previousDown
 -- One switch per press. Simultaneous directions cancel each other.
 if nextDown and previousDown then return end
 if nextPressed then S.step(1)elseif previousPressed then S.step(-1)end
end
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
