"""Native M20 Nero exists, but M19's selected Vergil remains manual."""
from pathlib import Path
import autoload_fixture as fixture

def setup(lua,native=0,outgoing=4):
    lua.globals().nextNative=native;lua.globals().outgoing=outgoing
    lua.execute('''
    mode=0;missionNo=19
    tick(fps*5);S.request(outgoing);tick(2)
    previous=active
    carried={};initialized={};for _,id in ipairs({0,1,4})do carried[id]=players[id];initialized[id]=players[id].initialized end
    savedLoads={};for _,id in ipairs({0,1,4})do savedLoads[id]=loads[id]or 0 end
    nativeOwner=actor(nextNative);nativeOwner.hp=12345
    players[nextNative]=nativeOwner;states[nextNative]=2
    missionNo=20;campaignID=nextNative
    beforeRestores=ownerRestores
    ''')

current=fixture.SOURCE
try:
    fixture.SOURCE=Path('work/checkpoints/release-36-before-native-owner-handoff/outputs')
    old=fixture.make_game(initial=1);setup(old)
    old.execute('''
    tick(fps*5)
    assert(active==previous and active.enabled and nativeOwner.enabled)
    assert(dmc5_switch_loader.awaitNative and dmc5_switch_loader.clock==0)
    ''')
finally:fixture.SOURCE=current

for initial,native,outgoing in [(1,0,4),(0,1,0),(4,4,0)]:
    lua=fixture.make_game(initial=initial);setup(lua,native,outgoing)
    lua.execute('''
    tick(fps*5)
    local B=dmc5_switch_loader
    assert(active==nativeOwner and not B.awaitNative and B.count==3)
    assert(ownerRestores==beforeRestores+1,'handoff was missing or repeated')
    assert(not previous.enabled and previous.paused and not previous.visible)
    assert(nativeOwner.initialized==0 and nativeOwner.hp==12345)
    for _,id in ipairs({0,1,4})do
     assert((loads[id]or 0)==savedLoads[id],'carried actor was loaded a second time')
     if id~=nextNative then
      assert(players[id]==carried[id])
      assert(players[id].initialized==initialized[id])
     end
    end
    S.request(outgoing);tick(fps)
    assert(active==previous and previous.enabled and not nativeOwner.enabled,'switching did not resume after handoff')
    ''')

for guard,release in [
    ('paused=true','paused=false'),
    ('nativeOwner.eventRun=true','nativeOwner.eventRun=false'),
    ('previous.eventRun=true','previous.eventRun=false'),
    ('nativeOwner.componentEnabled=false','nativeOwner.componentEnabled=true'),
    ('nativeOwner.updating=false','nativeOwner.updating=true'),
    ('nativeOwner.worldEnabled=false','nativeOwner.worldEnabled=true'),
    ('nativeOwner.noWorld=true','nativeOwner.noWorld=false'),
    ('nativeOwner.meshReady=false','nativeOwner.meshReady=true'),
    ('nativeOwner.hp=0','nativeOwner.hp=12345'),
]:
    lua=fixture.make_game(initial=1);setup(lua)
    lua.execute(guard)
    lua.execute('tick(fps);assert(active==previous and ownerRestores==beforeRestores)')
    lua.execute(release)
    lua.execute('tick(fps*3);assert(active==nativeOwner and ownerRestores==beforeRestores+1)')

print('PASS: release-36 permanent native-owner wait reproduced; ready native owner adopted once, outgoing actor parked immediately, carried actors not reloaded; HP/native initialization preserved; pause/events/mesh/component/update/physics/death guards; manual switching resumes')
