"""Exercise real switch + resource rules with ordered engine-call fixtures."""
import sys
from pathlib import Path
sys.path.insert(0, 'work/python-deps')
from lupa import LuaRuntime
from lua_test_support import install_input_profile_helper

lua = LuaRuntime()
lua.execute('''
Vector3f={new=function(x,y,z)return {x=x,y=y,z=z}end}
momentumVectors={'inertiaVector','inertiaVectorNew','inertiaTmp','inertiaVectorReserved'}
function clearMomentum(p)
 for _,name in ipairs(momentumVectors)do
  local v=p[name];v.x=0;v.y=0;v.z=0
 end
 p.inertiaTimer=0;p.speedY=0;p.speedXZ=0
end
log={};voiceCalls=0;hudCalls=0
after={}
function atHandoff(p)return p.position and p.position.x==10 and p.position.y==2 and p.position.z==30 end
function finishNative(staleWrite)
 if staleWrite then
  active.position=Vector3f.new(200,-100,300)
  active.pendingWarp=Vector3f.new(200,-100,300)
  active.worldEnabled=false
 end
 local pending=after;after={}
 for _,fn in ipairs(pending)do fn()end
 if staleWrite and active.worldEnabled then
  -- Physics retains its own world position. A Transform-only teleport can
  -- appear correct until the enabled controller writes its old point back.
  active.position=Vector3f.new(active.worldPosition.x,active.worldPosition.y,active.worldPosition.z)
 end
end
local action={get_name=function()return 'setCommandAction'end,
 get_param_types=function()return {{get_full_name=function()return 'app.Player.Actions'end},1,1,1,1,1,1}end,
 call=function(_,p,action,initAdd,initOverwrite)
  assert(initAdd and initOverwrite and p.form==0,'new action entered while transformed')
  assert(p.thinkReset and p.blendReset,'parked action state was not reset')
  p.action=action;clearMomentum(p);p.jumpCount=0
  p.position=Vector3f.new(100,-50,99);p.groundChecked=false
 end}
sdk={hook=function()end,find_type_definition=function()return {
 get_methods=function()return {action}end,get_method=function()return {}end}end}
sdk.get_managed_singleton=function(name)
 if name=='app.MissionSettingManager'then return {call=function()return setting end}end
 assert(name=='app.GameManager')
 return {get_field=function(_,n)assert(n=='PlayingID');return profile or 0 end,set_field=function(_,name,value)assert(name=='PlayingID');profile=value end,
  call=function(_,name)
   assert(name=='updatePlayerPadInput')
   if active and active.id==0 then active.padInput={}end
  end}
end
local runtime={withInputProfile=function(...)return realInputProfile(...)end,withControlProfile=function(...)return realControlProfile(...)end,selectManual=function(...)return realSelectManual(...)end,invalidate=function()end,afterUpdate=function(fn)after[#after+1]=fn end,
 permits=function()return not nativeV and active and(active.id==0 or active.id==1 or active.id==4)end}
dofile=function(path)
 if path:find('resources')then return resources end
 if path:find('runtime')then return runtime end
 if path:find('hud')then return {request=function()hudCalls=hudCalls+1 end}end
 if path:find('voice')then return {play=function()voiceCalls=voiceCalls+1 end}end
 return {apply=function()end}
end
function actor(id,form,active,air)
 local p={id=id,form=form,enabled=active,visible=active,paused=not active,
  hp=8000+id,dt=3700+id,sinGauge=6100+id,press=2,button=2,charge=3,timeline=true,
  speedY=air and 3.2 or 0,height=air and 2 or 0,phase=air and 1 or 0,jumpCount=1,speedXZ=4,
  doppel=id==4,clone=id==4,pending=id==4,transitions=0,think=true,grounded=not air,worldEnabled=active,subEnabled=false}
 p.padInput={}
 p.blueRose={input=p.padInput,call=function(self,name,arg)
  if name=='get_padInput'then return self.input
  elseif name=='set_padInput'then self.input=arg
  else assert(name=='forceEnd'or name=='reset')end
 end}
 function p:get_field(name)if name=='BlueRoseCharge'then return self.blueRose end;return nil end
 for i,name in ipairs(momentumVectors)do
  p[name]=Vector3f.new((active and 1 or -1)*(i+id+.5),-30-i,-i*2-id)
 end
 p.inertiaTimer=active and .35 or 9
 p.position=active and Vector3f.new(10,2,30)or Vector3f.new(100+id,-20,99)
 p.worldPosition=Vector3f.new(p.position.x,p.position.y,p.position.z)
 p.pendingWarp=Vector3f.new(100+id,-20,99)
 local transform={call=function(_,name)if name=='get_Position'then return p.position end;assert(name=='get_Rotation');return 'rotation'end}
 local object={call=function(_,name)assert(name=='get_Transform');return transform end}
 local med={call=function(_,name,v)
  if name=='set_drawSelf'then p.visible=v
  elseif name=='set_updateSelf'then p.updating=v
  else assert(name=='applyDrawSelf' or name=='applyUpdateSelf')end
 end}
 local component={call=function(_,name,v)assert(name=='set_Enabled' and v)end}
 local world={call=function(_,name,v)
  if name=='set_Enabled'then p.worldEnabled=v
  else assert(name=='get_Enabled');return p.worldEnabled end
 end}
 local sub={call=function(_,name,v)
  if name=='set_Enabled'then p.subEnabled=v
  else assert(name=='get_Enabled');return p.subEnabled end
 end}
 local clone={get_field=function(_,name)assert(name=='_DoppelValid');return p.clone end}
 function p:call(name,a,b,c,d)
  if name=='get_playerID'then return self.id
  elseif name=='get_padInput'then return self.padInput
  elseif name=='get_Enable'then return self.enabled
  elseif name=='resetGunShotReserve'or name=='finishBRChargeEffect'then
  -- Playable Vergil reports ordinary DT while Doppel Mode is enabled even
  -- when his own model is human. Human-form transition does not dismiss it.
  elseif name=='get_isDevilTrigger'then return self.form==1 or (self.id==4 and self.doppel)
  elseif name=='get_isTheDevilTrigger'then assert(id==1 or id==4);return self.form==2
  elseif name=='set_devilTriggerBtnOnTimer'then assert(a==0);self.button=a
  elseif name=='set_devilTriggerPressTimer'then assert(a==0);self.press=a
  elseif name=='set_isDevilTriggerTimeLineTriggered'then assert(a==false);self.timeline=a
  elseif name=='resetDevilTriggerPressCharge'then assert(id==1 or id==4);self.charge=0
  elseif name=='setDevilTrigger'then
   assert(a==0 and b==true);self.transitions=self.transitions+1
   log[#log+1]='human '..id
   if failedActor~=id then self.form=0;clearMomentum(self) end
  elseif name=='get_cachedDoppel'then return clone
  elseif name=='get_DoppelMode'then return self.doppel
  elseif name=='get_isGenerateDoppelWait'then return self.pending
  elseif name=='setDoppelMode'then assert(a==false);self.doppel=false;log[#log+1]='dismiss '..id
  elseif name=='set_isGenerateDoppelWait'then assert(a==false);self.pending=false
  elseif name=='destroyDoppelGanger'then self.clone=false
  elseif name=='get_cachedRequestSetCollider' or name=='get_cachedBehaviorTree'then return component
  elseif name=='get_cachedCharacterController'then return world
  elseif name=='get_cachedSubCharacterController'then return sub
  elseif name=='get_cachedActivateMediator'then return med
  elseif name=='set_MediationType' or name=='subNetworkSubType' or name=='updateNetworkCheckType' or name=='resetPadInput'then
  elseif name=='get_GameObject'then return object
  elseif name=='get_camera'then return camera
  elseif name=='set_camera'then assert(a==camera)
  elseif name=='get_speedY'then return self.speedY
  elseif name=='get_groundHeight'then return self.height
  elseif name=='isGround'then return self.grounded
  elseif (name=='get_isEventMove'or name=='get_isEventRun')then return self.eventRun or false
  elseif name=='set_groundCheckTimer'then assert(a==0);self.groundTimer=a
  elseif name=='checkGround'then
   assert(atHandoff(self) and self.groundTimer==0,'ground query before final warp')
   self.groundChecked=true
  elseif name=='get_jumpPhase'then return self.phase
  elseif name=='get_jumpCount'then return self.jumpCount
  elseif name=='get_jumpMoveSpeedXZ'then return self.speedXZ
  elseif name=='set_speedY'then self.speedY=a
  elseif name=='set_jumpPhase'then self.phase=a
  elseif name=='set_jumpCount'then self.jumpCount=a
  elseif name=='set_jumpMoveSpeedXZ'then self.speedXZ=a
  elseif name=='get_inertiaTimer'then return self.inertiaTimer
  elseif name=='set_inertiaTimer'then self.inertiaTimer=a
  elseif name:match('^get_inertia')then
   local key=name:sub(5);assert(self[key]);return self[key]
  elseif name:match('^set_inertia')then
   local key=name:sub(5);assert(self[key]);self[key]=Vector3f.new(a.x,a.y,a.z)
  elseif name=='get_playerData'then return {set_field=function()end}
  elseif name=='set_Enable'then self.enabled=a
  elseif name=='resumePlayer'then self.paused=false
  elseif name=='set_isThinkEnable'then self.think=a
  elseif name=='resetThink'then
   if failedEntry==name then error('entry reset failure')end
   assert(a==true and b==-1);self.thinkReset=true;self.entryResets=(self.entryResets or 0)+1
  elseif name=='resetBlendRateLock'then
   if failedEntry==name then error('entry reset failure')end
   self.blendReset=true
  elseif name=='pausePlayer'then self.paused=true;log[#log+1]='pause '..id
  elseif name=='warp'then
   assert(a.x==10 and a.y==2 and a.z==30 and b=='rotation')
   self.position=Vector3f.new(a.x,a.y,a.z)
   if d then self.worldPosition=Vector3f.new(a.x,a.y,a.z)end
  elseif name=='processWarpRequest'then
   if self.pendingWarp then self.position=self.pendingWarp;self.pendingWarp=nil end
  else error('Unexpected player operation '..name)end
 end
 -- Native Player.doCharacterUpdateCommon routes manual command handling
 -- around the AI branch only when IsThinkEnable is false (TDB67).
 function p:acceptsManualInput()
  return self.enabled and not self.paused and not self.think
 end
 return p
end
function scenario(oldID,newID,oldForm,newForm,air,failID)
 failedActor=failID;log={};voiceCalls=0;hudCalls=0;after={}
 old=actor(oldID,oldForm,true,air);new=actor(newID,newForm,false,false);active=old
 local accessor={call=function(_,name,p)assert(name=='set_player');cameraTarget=p end,set_field=function()end}
 camera={call=function(_,name)assert(name=='get_player');return accessor end,set_field=function()end}
 controlID=oldID
 local function handoff(id)
  if id==newID then
   assert(old.form==0 and new.form==0,'control transferred before DT exit')
   assert(not old.doppel and not old.pending and not old.clone,'departing Doppel survived handoff')
   assert(not new.doppel and not new.pending and not new.clone,'reserve Doppel survived handoff')
   log[#log+1]='handoff';active=new;clearMomentum(new)
  else assert(id==oldID);active=old end
 end
 setting={call=function(_,name,id)if name=='get_ControllPlayerID'then return controlID end;assert(name=='set_ControllPlayerID');controlID=id end}
 manager={call=function(_,name,id)
  if name=='get_manualPlayer'then return active
  elseif name=='getPlayerByID'then return id==oldID and old or new
  else assert(name=='updateManualPlayer');handoff(controlID)end
 end}
end
''')
resources = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_resources.lua').read_text())
lua.globals().resources = resources
install_input_profile_helper(lua)
core = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
lua.globals().core = core
forms = {0: (0, 1), 1: (0, 1, 2), 4: (0, 1, 2)}
for previous in forms:
    for target in forms:
        if previous == target:
            continue
        for old_form in forms[previous]:
            for new_form in forms[target]:
                for air in (False, True):
                    lua.globals().scenario(previous, target, old_form, new_form, air, -1)
                    source = lua.globals().old
                    core.switch(lua.globals().manager, target)
                    lua.globals().finishNative(True)
                    lua.execute('''
assert(active==new and old.form==0 and new.form==0)
if active.id==0 then assert(active.blueRose.input==active.padInput,'charge bound before native profile refresh')end
assert(old.paused and not old.enabled and not old.visible)
assert(not new.paused and new.enabled and new.visible)
assert(new.worldEnabled and not old.worldEnabled and not old.subEnabled,'world collision not transferred with control')
assert(new:acceptsManualInput() and not old:acceptsManualInput(),'handoff left manual input on AI path')
assert(new.press==0 and old.press==0 and new.button==0 and old.button==0)
assert(not new.timeline and not old.timeline)
for _,p in ipairs({old,new})do
 assert(p.hp==8000+p.id and p.dt==3700+p.id and p.sinGauge==6100+p.id,'explicit gauge/HP write')
 if p.id==1 or p.id==4 then assert(p.charge==0)end
end
assert(cameraTarget==new and voiceCalls==1 and hudCalls==1)
local handoff,park
for i,event in ipairs(log)do if event=='handoff'then handoff=i elseif event=='pause '..old.id then park=i end end
assert(handoff and park and handoff<park)
for i,event in ipairs(log)do if event:find('human')then assert(i<handoff,'late DT exit')end end
''')
                    p = lua.globals().new
                    for name in ('inertiaVector', 'inertiaVectorNew', 'inertiaTmp', 'inertiaVectorReserved'):
                        assert tuple(p[name][axis] for axis in ('x', 'y', 'z')) == (0, 0, 0), name
                    assert p.inertiaTimer == 0 and p.speedXZ == 0 and p.speedY == 0
                    assert lua.globals().atHandoff(p) and p.groundChecked and p.pendingWarp is None
                    assert (p.worldPosition.x,p.worldPosition.y,p.worldPosition.z)==(10,2,30)
                    assert p.action == (75 if air else 1)
                    if air:
                        assert p.phase == 4 and p.jumpCount == 1
                    # Same-actor control repair must not prohibit manual DT during play.
                    p.form = 1
                    core.switch(lua.globals().manager, target)
                    lua.globals().finishNative(True)
                    assert p.form == 1 and p.acceptsManualInput(p)
                    assert p.entryResets == 1, 'same actor selection cancelled current action'

# Zero-speed entry must erase both source and parked target motion, regardless
# of incoming direction, native pending displacement or vertical contact speed.
for previous in forms:
    for target in forms:
        if previous == target:
            continue
        for airborne in (False, True):
            for x, z in ((0, 0), (-12, 0), (0, 9), (7, -11)):
                for speed_y in ((-6, 0, 4) if airborne else (-25, -.2, 0, .005)):
                    lua.globals().scenario(previous, target, 0, 0, airborne, -1)
                    old = lua.globals().old
                    old.speedY = speed_y
                    old.speedXZ = abs(x) + abs(z)
                    old.inertiaTimer = .125 if x or z else 0
                    for name in ('inertiaVector', 'inertiaVectorNew', 'inertiaTmp', 'inertiaVectorReserved'):
                        old[name] = lua.globals().Vector3f.new(x, -50, z)
                    core.switch(lua.globals().manager, target)
                    p = lua.globals().new
                    assert p.speedY == 0 and p.speedXZ == 0
                    assert p.action == (75 if airborne else 1)
                    assert lua.globals().atHandoff(p) and p.groundChecked and p.pendingWarp is None
                    for name in ('inertiaVector', 'inertiaVectorNew', 'inertiaTmp', 'inertiaVectorReserved'):
                        assert (p[name].x, p[name].y, p[name].z) == (0, 0, 0)
                    assert p.inertiaTimer == 0

# Upward takeoff can precede the native ground flag clearing by one tick.
lua.globals().scenario(0, 1, 0, 0, False, -1)
lua.globals().old.speedY = 4
core.switch(lua.globals().manager, 1)
assert lua.globals().new.action == 75 and lua.globals().new.speedY == 0
assert lua.globals().new.phase == 4 and lua.globals().new.jumpCount == 1

# Selecting the already-controlled actor is a control repair, not a handoff;
# never clear movement continuously or erase manual movement on this path.
lua.globals().new.speedY = -3
lua.globals().new.speedXZ = 6
core.switch(lua.globals().manager, 1)
assert lua.globals().new.speedY == -3 and lua.globals().new.speedXZ == 6

for failed in (0, 4):
    lua.globals().scenario(0, 4, 1, 2, True, failed)
    lua.execute('''
local ok=pcall(core.switch,manager,4)
assert(not ok and active==old,'DT exit failure transferred control')
assert(old.enabled and not old.paused and old.visible)
assert(old.worldEnabled and not new.worldEnabled,'failed switch left world collision on the wrong actor')
assert(old:acceptsManualInput(),'rollback did not restore manual input')
assert(not new.enabled and new.paused and not new.visible)
assert(voiceCalls==0 and hudCalls==0)
for _,event in ipairs(log)do assert(event~='handoff')end
''')

for failed in ('resetThink', 'resetBlendRateLock'):
    lua.globals().scenario(0, 1, 0, 0, True, -1)
    lua.globals().failedEntry = failed
    lua.execute('''
local ok,why=pcall(core.switch,manager,1)
assert(not ok and tostring(why):find('entry reset failure'))
assert(active==old and old.enabled and not old.paused and old.visible)
assert(old.worldEnabled and not new.worldEnabled,'entry rollback lost world collision')
assert(old:acceptsManualInput(),'entry failure left original actor on AI path')
assert(not new.enabled and new.paused and not new.visible)
assert(cameraTarget==old and voiceCalls==0 and hudCalls==0)
for _,event in ipairs(log)do assert(event~='handoff')end
''')
    lua.globals().failedEntry = None

lua.execute('''
for _,sourceID in ipairs({0,4})do
 scenario(sourceID,1,0,0,true,-1)
 assert(not new.worldEnabled,'fixture must begin with parked physics disabled')
 core.switch(manager,1);finishNative(true)
 -- A Cerberus-style root-motion dive bypasses speedY. The world controller
 -- must still block its downward transform displacement at the floor.
 for i=1,40 do
  new.position.y=new.position.y-.25
  if new.worldEnabled then new.position.y=math.max(2,new.position.y)end
 end
 assert(new.position.y==2 and new.speedY==0,'root-motion dive bypassed world collision')
 new.worldEnabled=false
 finishNative(false)
 assert(not new.worldEnabled,'idle frames override native action collision modes')
end

-- Source transforms and target native writes remain mutable through the
-- engine tick. Completion must use the captured handoff location once.
scenario(0,1,0,0,false,-1)
core.switch(manager,1)
old.position.x=-999
finishNative(true)
assert(atHandoff(new) and new.pendingWarp==nil,'deferred native warp or physics restored parked position')
new.position=Vector3f.new(11,2,30)
finishNative(false)
assert(new.position.x==11,'placement pinned normal movement on subsequent frames')

scenario(0,1,0,0,false,-1)
dmc5_switch_loader={manager=manager,generation=1}
core.switch(manager,1)
dmc5_switch_loader.generation=2
finishNative(true)
assert(new.position.x==200,'old-scene completion leaked into a new scene')
dmc5_switch_loader=nil

scenario(0,1,0,0,false,-1)
core.switch(manager,1)
new.eventRun=true
finishNative(true)
assert(new.position.x==200,'completion overwrote an event-controlled position')

scenario(0,1,0,0,false,-1)
core.switch(manager,1)
core.switch(manager,0)
finishNative(true)
assert(active==old and atHandoff(old),'superseded completion moved the wrong actor')

local unrelated={call=function(_,name)assert(name=='get_playerID');return 2 end}
assert(resources.retire(unrelated)==false)
''')

lua.execute('''
scenario(0,1,0,0,false,-1)
local extra=actor(2,0,true,false)
extra.eventRun=true
assert(not core.parkNonParty(manager,extra) and extra.visible and extra.enabled)
extra.eventRun=false
assert(core.parkNonParty(manager,extra))
assert(extra.paused and not extra.enabled and not extra.visible and extra.updating==false)
assert(not extra.worldEnabled and not extra.subEnabled)
assert(extra.entryResets==nil and active==old and old.enabled and old.visible)
assert(extra.hp==8002 and extra.dt==3702 and extra.action==nil)
assert(not core.parkNonParty(manager,new),'supported reserve was mistaken for V')
active=extra
assert(not core.parkNonParty(manager,extra),'manual V was parked')
assert(not core.parkNonParty(manager,new),'V campaign changed another actor')
''')
lua.execute('''
scenario(0,1,0,0,false,-1)
core.switch(manager,1)
new.visible=false;new.updating=false
finishNative(false)
assert(new.visible and new.updating,'late native parking flags hid the selected model')
new.visible=false;finishNative(false)
assert(not new.visible,'ordinary native actions had visibility pinned')
core.switch(manager,1)
assert(new.visible and new.enabled and not new.paused,'same-actor recovery left model hidden')
''')
print('PASS: all pairs/forms; one-shot placement/visibility survive delayed native writes; scene/event/superseded completions skipped; no ordinary action pinning; same-actor visibility, zero-speed, collision and rollback retained.')
lua.execute('''
scenario(0,1,0,0,false,-1)
core.switch(manager,1);finishNative(false)
local hp,dt,sin,pos,action=new.hp,new.dt,new.sinGauge,new.position,new.action
new.enabled=false;new.visible=false;new.paused=true
core.recoverSelected(manager,new)
assert(new.enabled and new.visible and not new.paused and new.worldEnabled)
assert(new.hp==hp and new.dt==dt and new.sinGauge==sin and new.position==pos and new.action==action and #after==0)
scenario(0,1,0,0,false,-1)
core.switch(manager,1);nativeV=true;finishNative(true)
assert(new.position.x==200,'old deferred placement escaped into a native V scene')
nativeV=nil
''')
