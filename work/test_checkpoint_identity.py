"""Restart Checkpoint must not persist the current reserve as the native hero."""
import autoload_fixture as fixture

def prepare(native, selected):
    lua=fixture.make_game(initial=native)
    lua.globals().selected=selected
    lua.execute('''
    mode=0;missionNo=3;campaignID=initial_id;B=dmc5_switch_loader;tick(fps*5)
    S.request(selected);tick(2)
    control=initial_id;entered=true
    setting={call=function(_,n,v)
     if n=='get_ControllPlayerID'then return control end
     assert(n=='set_ControllPlayerID');control=v
    end}
    settingManager={call=function(_,n)
     if n=='get_isEntered'then return entered end
     assert(n=='get_Setting');return setting
    end}
    function checkpoint(protected)
     local h=protected and nativeHooks['app.MissionSettingManager.restartMissionCheckPoint']
     if h then h[1]({[2]=settingManager})end
     nativeIncoming=control
     control=selected -- native scheduling writes the currently selected ID
     if h then assert(h[2](123)==123,'checkpoint native return changed')end
     spawnedID=control
    end
    function construct()
     players={};states={};loadAt={};finishAt={};unregistered={}
     players[spawnedID]=actor(spawnedID);active=players[spawnedID]
     dmc5_switch_runtime.invalidate()
    end
    ''')
    return lua

old=prepare(0,4)
old.execute('checkpoint(false);construct();tick(fps*5);assert(spawnedID==4 and B.awaitNative and not B.playable)')
for native in (0,1,4):
    for selected in (0,1,4):
        lua=prepare(native,selected)
        lua.execute('''
        assert(nativeHooks['app.MissionSettingManager.restartMissionCheckPoint'])
        checkpoint(true);assert(nativeIncoming==initial_id and spawnedID==initial_id)
        assert(dmc5_switch_runtime.storyRetrySerial==1)
        construct();tick(fps*6)
        assert(active.id==initial_id and B.count==3 and not B.awaitNative, 'active='..active.id..' count='..tostring(B.count)..' await='..tostring(B.awaitNative)..' reload='..tostring(dmc5_switch_runtime.storyReload and dmc5_switch_runtime.storyReload.phase)..' error='..tostring(dmc5_switch_runtime.storyRetryError))
        local target=initial_id==4 and 0 or 4
        S.request(target);tick(2);assert(active.id==target,'switching did not recover')
        selected=target;checkpoint(true);assert(spawnedID==initial_id)
        ''')

from mission_control_fixture import make_game
lua=make_game()
lua.execute('''
R.manager=manager;manager:call('updateManualPlayer')
nativeID=2 -- stale task lookup; the captured, same-scene native route is Nero
assert(not R.permits(manager));assert(R.prepareStoryRetry(settingManager))
assert(R.storyRetryID==0 and setting.id==0)
local serial=R.storyRetrySerial
setting.id=4;assert(R.finishStoryRetry(settingManager,serial));assert(setting.id==0)
assert(not R.finishStoryRetry(settingManager,serial),'completed reload applied twice')
assert(R.prepareStoryRetry(settingManager));local serial=R.storyRetrySerial
setting.id=4;mission=19
assert(not R.finishStoryRetry(settingManager,serial)and setting.id==4,'stale completion changed new mission')
''')
print('PASS: M3 checkpoint selection leak and stuck owner reproduced; all three native heroes and selections recover, repeated checkpoints, pre/post native writes, stale task lookup and new-mission completion isolation covered')

# Captured pre-0.0.3 failure: the pre/post callback ran (retry=1), but later
# loading phases replaced settings and wrote Vergil again after it returned.
for native in (0,1,4):
    lua=prepare(native,4 if native!=4 else 1)
    lua.execute('''
    checkpoint(true)
    local R=dmc5_switch_runtime;local outgoing=players[initial_id]
    active=outgoing;tick(5)
    assert(R.storyReload and not S.request(1),'outgoing actor ended the reload guard')
    setting={call=function(_,n,v)
     if n=='get_ControllPlayerID'then return control end
     assert(n=='set_ControllPlayerID');control=v
    end}
    for i=1,10 do control=selected;tick(1);assert(control==initial_id and R.storyReload)end
    assert(R.storyReload.repairs>=10 and not B.task,'late settings overwrite was accepted or reserves warmed during reload')
    active=nil;R.invalidate();tick(1)
    assert(R.storyReload and R.storyReload.teardown)
    construct();active.meshReady=false
    tick(20);assert(R.storyReload and not B.task,'cold incoming actor released the guard')
    active.meshReady=true;tick(fps*6)
    assert(R.storyReload==nil and active.id==initial_id and B.count==3)
    assert(control==initial_id,'new native route was not retained')
    ''')
print('PASS: delayed post-return ID overwrites and replacement settings repaired across teardown; outgoing/cold actors cannot end guard; no reserve loading during reload; guard ends only on ready native arrival')
