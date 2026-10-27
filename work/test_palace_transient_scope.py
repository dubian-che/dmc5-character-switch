"""A transfer snapshot must outlive the native gap with no manual player."""
from palace_test_fixture import make_game

for selected in (0, 1, 4):
    lua=make_game()
    lua.globals().selected=selected
    lua.execute('''
    bp.CurrentStageNo=0;bp.IsGauntletStage=true
    phase('updateGauntletStageInit')
    players[0].armList=arms({3,1,7,2});players[0].count=4
    choose(selected,'user')
    local beforeHp=players[selected].hp
    phase('updateFadeout')
    assert(Palace.run.stage.closed and Palace.run.stage.snapshot.rows[0].stock[1]==3)
    local committed=Palace.run.stage.snapshot
    -- The native handoff detaches the outgoing manual player before its
    -- remaining finalize and manager-update callbacks have stopped.
    active=nil;Runtime.invalidate()
    frames(3)
    phase('updateGauntletStageFinalize')
    assert(Palace.run and Palace.run.stage.snapshot==committed,
      'normal loading erased committed inventory/selected-character snapshot')
    assert(not Palace.canRefill(),'empty native initialization triggered a new random arm')
    -- Native creation finishes with Vergil temporarily manual. The saved
    -- user selection and ordered inventory still own the arriving epoch.
    reload('battle',1)
    settle()
    assert(active.id==selected,'native transient selection replaced the user choice')
    assert(players[selected].hp==beforeHp)
    assert(players[0].count==4 and players[0].armList.values[1]==3 and
      players[0].armList.values[2]==1 and players[0].armList.values[3]==7 and
      players[0].armList.values[4]==2)
    assert(Palace.restores==3)
    -- Missing manager readiness is transient, leaving Palace is definitive.
    phase('updateFadeout');active=nil;Runtime.invalidate();frame()
    assert(Palace.run)
    mode=0;frame();assert(Palace.run==nil)
    ''')
print('PASS: supply exit retains all three selections, ordered arms and vitals across detached native control; loading cannot refill empty stock; leaving Palace still resets')
