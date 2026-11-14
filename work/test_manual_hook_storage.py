"""Model the pinned loader clearing current storage after a nested lookup."""
from mission_control_fixture import make_game

lua = make_game()
lua.execute('''
R.manager=manager
manager:call('updateManualPlayer')
R.selectManual(manager,setting,4)
local outer={}
local original=R.maintainStoryReload
R.maintainStoryReload=function(m)
 original(m)
 -- A nested getPlayerByID post-hook pops its table and leaves current nil.
 storage=nil
end
storage=outer
hooks.updateManualPlayer[1]({[2]=manager})
assert(R.controlIdentityError==nil,R.controlIdentityError)
assert(setting.id==4,'selected identity was not applied')
assert(outer.manualIdentityFrames[1].previous==0)
-- The loader selects the original invocation's table before its post-hook.
storage=outer
assert(hooks.updateManualPlayer[2](123)==123)
assert(setting.id==0,'native identity was not restored')
assert(outer.manualIdentityFrames==nil)
''')
print('PASS: nested hook clears current storage; outer selection and restoration survive')
