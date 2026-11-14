"""A completed reserve task must not leak a late native ID write."""
from mission_control_fixture import make_game
from autoload_fixture import make_game as autoload

for route in (0, 1, 4):
    lua = make_game()
    lua.globals().route = route
    lua.execute('''
    setting.id=route;nativeID=route;active=players[route]
    R.manager=manager;manager:call('updateManualPlayer')
    local B=dmc5_switch_loader
    R.begin(manager);B.task={id=4};R.guardReserveIdentity(manager)
    -- Lua finished preparing the reserve before the engine's final write.
    B.task=nil;setting.id=route==4 and 1 or 4
    local captured=R.nativeControl
    R.nativeControl={manager=manager,setting=setting,id=setting.id,mode=0,mission=mission}
    assert(setting.id~=route)
    R.finish()
    assert(setting.id==route and R.reserveIdentityRepairs==1 and R.nativeControl==captured)
    manager:call('updateManualPlayer')
    assert(active.id==route and R.nativeControl.id==route)
    local target=route==4 and 0 or 4
    R.selectManual(manager,setting,target)
    assert(active.id==target and setting.id==route)
    -- No recurring pin after the load boundary: genuine native handoff works.
    setting.id=2;nativeID=2
    manager:call('updateManualPlayer')
    assert(active.id==2 and R.nativeControl.id==2)
    ''')

for transition in ("mission=19", "setting=newSetting(4)",
                   "dmc5_switch_loader.generation=2",
                   "R.storyRetrySerial=1", "mode=3"):
    lua = make_game()
    lua.execute('''
    R.manager=manager;manager:call('updateManualPlayer')
    R.begin(manager);R.guardReserveIdentity(manager);setting.id=4
    ''')
    lua.execute(transition)
    lua.execute("R.finish();assert(setting.id==4,'stale load changed new scene')")

# Use actual key polling, request, queue and switching modules after teardown.
lua = autoload(initial=0, config={"version": 1, "nextKey": 66, "previousKey": 112,
                                 "controllerCombo": False})
lua.execute('''
tick(fps*5);S.request(4);tick(2)
players={};states={};loadAt={};finishAt={};unregistered={}
players[0]=actor(0);active=players[0]
dmc5_switch_runtime.invalidate()
S.stage='checkpoint reload in progress'
tick(fps*5)
assert(S.stage=='active Nero' and dmc5_switch_loader.count==3)
key_down[66]=true;tick(2);assert(active.id==1)
key_down[66]=false;tick(1)
key_down[112]=true;tick(2);assert(active.id==0)
assert(S.keyPressCount==2 and S.lastRequest.accepted and S.switchCount==3)
dmc5_switch_runtime.storyReload={}
assert(not S.request(4))
assert(S.lastRequest.reason=='checkpoint reload' and not S.lastRequest.accepted)
''')
print('PASS: late reserve identity writes repaired after native completion; three routes, scene/setting/generation/retry boundaries, genuine native V handoff, B/F1 after reconstruction and rejected-request diagnostics')
