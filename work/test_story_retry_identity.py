from pathlib import Path
import autoload_fixture as fixture

def prepare(lua):
    lua.execute('''
    mode=0;missionNo=20;campaignID=initial_id
    tick(fps*5);S.request(4);tick(2)
    control=4;identityWrites=0;entered=true
    setting={call=function(_,n,v)
     if n=='get_ControllPlayerID'then return control end
     assert(n=='set_ControllPlayerID');control=v;identityWrites=identityWrites+1
    end}
    settingManager={call=function(_,n)
     if n=='get_isEntered'then return entered end
     assert(n=='get_Setting');return setting
    end}
    function requestRetry()
     local h=nativeHooks['app.MissionSettingManager.retryMission']
     if h then h[1]({[2]=settingManager})end
     spawnedID=control -- native constructor reads the mission setting
     if h then assert(h[2](123)==123,'native retry return changed')end
    end
    function constructRetry()
     players={};states={};loadAt={};finishAt={};unregistered={}
     players[spawnedID]=actor(spawnedID);active=players[spawnedID]
     dmc5_switch_runtime.invalidate()
    end
    ''')

current=fixture.SOURCE
try:
    fixture.SOURCE=Path('work/checkpoints/release-37-before-story-retry-boundary/outputs')
    old=fixture.make_game(initial=0);prepare(old)
    old.execute('''
    requestRetry();constructRetry();tick(fps*5)
    assert(spawnedID==4 and players[0]==nil and active.id==4)
    assert(dmc5_switch_loader.awaitNative and not dmc5_switch_loader.playable)
    ''')
finally:fixture.SOURCE=current

lua=fixture.make_game(initial=0);prepare(lua)
lua.execute('''
local B=dmc5_switch_loader
local old=active;local generation=B.generation;local restores=ownerRestores
B.task={id=0,phase='load',owner=old,ownerID=4,start=B.clock}
S.request(1)
requestRetry()
assert(spawnedID==0 and identityWrites==1 and active==old,'retry prehook changed the live actor')
-- Native control update during the outgoing fade must not be undone by the old queue.
active=players[0];paused=true;dmc5_switch_runtime.invalidate();tick(1)
assert(B.generation==generation+1 and not B.task and ownerRestores==restores)
constructRetry();paused=false;tick(fps*6)
assert(active.id==0 and B.count==3 and not B.awaitNative and switches==1)
assert(not loads[0],'native retry hero was loaded again')
S.request(4);tick(fps)
assert(active.id==4 and switches==2,'switching did not resume after Retry Mission')
''')

for native in (0,1,4):
    for selected in (0,1,4):
        lua=fixture.make_game(initial=native);prepare(lua)
        lua.globals().nativeID=native;lua.globals().selected=selected
        lua.execute('''
        mode=0;campaignID=nativeID;active=players[selected];control=selected
        dmc5_switch_runtime.invalidate()
        requestRetry();assert(spawnedID==nativeID)
        assert(identityWrites==(selected==nativeID and 0 or 1))
        ''')

for setup in ('mode=3','mode=1','campaignID=2','active=actor(2)','entered=false'):
    lua=fixture.make_game(initial=0);prepare(lua)
    lua.execute(setup)
    lua.execute('''
    dmc5_switch_runtime.invalidate()
    requestRetry();assert(control==4 and identityWrites==0)
    assert(dmc5_switch_runtime.storyRetrySerial==nil)
    ''')

print('PASS: release-37 retry spawns wrong hero and waits forever reproduced; confirmed retry restores native story identity before construction; outgoing queue cannot reclaim control; full party and switching recover; all three native campaigns, Palace/Void/V/unentered exclusions and native return preserved')
