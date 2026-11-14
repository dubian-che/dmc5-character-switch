from pathlib import Path
from lupa import LuaRuntime
lua=LuaRuntime()
lua.execute("""
dofile=function()return {}end
ends=0;clears=0;inits=0
sdk={find_type_definition=function()return {get_methods=function()return {}end}end,
get_managed_singleton=function(n)assert(n=='app.AppEffectManager');return {call=function(_,m)
 if fail then error('unavailable')end
 if m=='ClearLDRPostProcess'then clears=clears+1 else assert(m=='initLDRPostProcessParam');inits=inits+1 end
end}end}
object={}
player={call=function(_,n)if n=='get_playerID'then return id elseif n=='get_isTheDevilTrigger'then return sin else assert(n=='get_GameObject');return object end end}
camera={call=function(_,n,v)
 if n=='get_isFinishCamera'then return finish end
 if n=='isFinishCameraTarget'then assert(v==object);return owned end
 assert(n=='EndFinishCamera'and v==true);ends=ends+1
end}
""")
lua.globals().M=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
lua.execute("""
for _,pid in ipairs({0,1,4})do
 id=pid;sin=false;finish=false;owned=false
 M.finishPresentation(M.capturePresentation(player,camera))
end
assert(ends==0 and clears==0)
id=1;sin=true;finish=true;owned=true
local captured=M.capturePresentation(player,camera);sin=false
M.finishPresentation(captured)
assert(ends==1 and clears==1 and inits==1)
finish=true;owned=false
M.finishPresentation(M.capturePresentation(player,camera))
assert(ends==1 and clears==1,'unrelated camera or ordinary state cleared')
sin=true;fail=true
M.finishPresentation(M.capturePresentation(player,nil))
assert(M.presentationError and ends==1,'optional effect failure escaped or was hidden')
""")
print('PASS: outgoing SDT captured before retirement; only owned special camera ended; ordinary/unrelated cameras untouched; optional failure reported.')
