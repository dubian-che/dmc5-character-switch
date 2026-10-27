from pathlib import Path
import autoload_fixture as fixture

def duplicates(lua):
    lua.execute('''
    tick(fps*5);S.request(4);tick(1)
    originalNero=actor(0);unregistered={originalNero}
    tick(fps)
    ''')

current=fixture.SOURCE
try:
    fixture.SOURCE=Path('work/checkpoints/release-35-before-story-instance-ownership/outputs')
    old=fixture.make_game(initial=0);duplicates(old)
    old.execute('''
    assert(active.id==4 and active.enabled)
    assert(not players[0].enabled and originalNero.enabled,'old duplicate control not reproduced')
    ''')
finally:fixture.SOURCE=current

for owner,duplicateID in [(4,0),(0,1),(1,4)]:
    lua=fixture.make_game(initial=0)
    lua.globals().owner=owner;lua.globals().duplicateID=duplicateID
    lua.execute('''
    tick(fps*5);S.request(owner);tick(1)
    local duplicate=actor(duplicateID)
    local boss=actor(3);local clone=actor(4);clone.isDoppel=true
    local enemyDante=actor(1);enemyDante.enemyDante=true
    local eventActor=actor(0);eventActor.eventRun=true
    unregistered={duplicate,boss,clone,enemyDante,eventActor}
    tick(fps)
    assert(active.id==owner and active.enabled and active.visible)
    assert(not duplicate.enabled and not duplicate.visible and duplicate.paused)
    assert(boss.enabled and clone.enabled and enemyDante.enabled and eventActor.enabled)
    local repairs=duplicate.parkings;tick(fps*10);assert(duplicate.parkings==repairs)
    eventActor.eventRun=false;tick(fps);assert(not eventActor.enabled)
    duplicate.enabled=true;duplicate.visible=true;duplicate.updating=true
    tick(fps);assert(duplicate.parkings==repairs+1 and not duplicate.enabled)
    ''')

lua=fixture.make_game(initial=1)
lua.execute('''
mode=0;missionNo=19;campaignID=1
tick(fps*5);S.request(4);tick(1);assert(active.id==4)
local B=dmc5_switch_loader
local generation=B.generation;local restores=ownerRestores
local nativeNeroLoads=loads[0]
-- Same PlayerManager, old Vergil still manual and a stale load owner ticket.
B.task={id=0,phase='load',owner=active,ownerID=4,start=B.clock}
missionNo=20;campaignID=0
tick(fps)
assert(B.generation==generation+1 and B.awaitNative and not B.task)
assert(not B.playable and ownerRestores==restores,'old queue undid the native handoff')
-- The engine, not the Mod, installs M20's Nero after its event.
players[0]=actor(0);active=players[0]
players[1]=nil;players[4]=nil;states[0]=nil;states[1]=nil;states[4]=nil
loadAt={};finishAt={}
event=true;tick(fps);assert(B.awaitNative and not B.task)
event=false;tick(fps*6)
assert(not B.awaitNative and B.count==3 and active==players[0])
assert(loads[0]==nativeNeroLoads,'native M20 owner was loaded a second time')
''')
print('PASS: old duplicate-input instance reproduced; Nero/Dante/Vergil duplicates parked by object, boss/clone/events protected, settled objects unchanged, native M19->M20 handoff precedes warm-up without duplicate native-owner loads')
