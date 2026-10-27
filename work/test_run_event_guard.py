"""Ordinary locomotion must never be mistaken for native scripted movement."""
from pathlib import Path
from mission_control_fixture import make_game
import autoload_fixture as fixture

old=Path('work/checkpoints/release-46-before-run-event-guard/outputs/DMC5CharacterSwitch')

def control_check(source,broken):
    for owner,target in [(1,0),(0,1),(1,4)]:
        lua=make_game(source/'dmc5_switch_runtime.lua')
        lua.globals().owner=owner;lua.globals().target=target;lua.globals().broken=broken
        lua.execute('''
        mission=19;nativeID=owner;setting=newSetting(owner);active=players[owner]
        dmc5_switch_loader.storyMission=19;R.manager=manager
        manager:call('updateManualPlayer')
        R.selectManual(manager,setting,target)
        players[owner].visible=false;players[target].visible=true
        players[target].running=true -- native MoveLoop + moveBlendRate >= .5
        manager:call('updateManualPlayer')
        if broken then
          assert(active==players[owner]and not active.visible and R.controlSelection==nil,
            'release-46 invisible parked-native-owner bug not reproduced')
        else
          for _=1,600 do
            manager:call('updateManualPlayer')
            assert(active==players[target]and active.visible and R.controlSelection.id==target)
            assert(setting.id==owner,'native battle-route identity leaked while running')
          end
          players[target].event=true -- actual native EventMove category
          manager:call('updateManualPlayer')
          assert(active==players[owner]and R.controlSelection==nil,'scripted movement handoff bypassed')
        end
        ''')

control_check(old,True)
control_check(fixture.SOURCE,False)

for source,broken in [(old,True),(fixture.SOURCE,False)]:
    previous=fixture.SOURCE
    try:
        fixture.SOURCE=source;lua=fixture.make_game()
    finally:fixture.SOURCE=previous
    lua.globals().broken=broken
    lua.execute('''
    tick(fps*5)
    for _,p in pairs(players)do
      local original=p.call
      p.call=function(self,n,...)
       if n=='get_isEventRun'then return true end
       return original(self,n,...)
      end
    end
    S.request(4);tick(1)
    if broken then assert(active.id==0 and not dmc5_switch_loader.playable)
    else
      assert(active.id==4 and switches==1 and dmc5_switch_loader.playable,'running delayed a ready switch')
    end
    ''')

for p in fixture.SOURCE.glob('*.lua'):
    assert 'get_isEventRun' not in p.read_text(),f'unreviewed movement-as-event guard: {p}'
print('PASS: release-46 invisible native fallback and running switch delay reproduced; all three running heroes retain control for 1800 native refreshes; true scripted movement still hands off; all production call sites audited.')
