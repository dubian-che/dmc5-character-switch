"""Checkpoint standby must be cleared before native action admission."""
import runpy
l=runpy.run_path('work/test_world_v_camera.py')['l']
l.execute('''
allowed=true;summoned=true;clone=false;wrongOwner=false;ownerID=4;enabled=true
local bits=129;local check=1;local treeEnabled=false;local writes=0
local tree={call=function(_,n,v)
 if n=='get_Enabled'then return treeEnabled end
 assert(n=='set_Enabled'and v==true);treeEnabled=v
end}
summon.call=function(_,n,v)
 if n=='get_playerID'then return 2 end
 if n=='get_ownerVergilPL'then return wrongOwner and foreignV or owner end
 if n=='get_Enable'then return enabled end
 if n=='get_cachedBehaviorTree'then return tree end
 if n=='subNetworkSubType'then assert(v==1 or v==2);bits=bits & (~v);writes=writes+1;return end
 if n=='updateNetworkCheckType'then check=(bits & 3)~=0 and 1 or 16;return end
 error(n)
end
local function nativeAction()return check==16 and treeEnabled end
assert(not nativeAction(),'checkpoint failure fixture did not reject action')
assert(R.worldVActionHooked and not R.worldVActionError)
local hook=hooks['app.PlayerV.setAction']
hook[1]({[2]=summon,[3]=28})
assert(nativeAction(),'native action still rejected after preparation')
assert(bits==128 and writes==2,'unrelated subtype flags changed')
assert(hook[2](123)==123)
for _,case in ipairs({'scene','inactive','clone','owner','disabled','action','foreign','hero'})do
 allowed=case~='scene';summoned=case~='inactive';clone=case=='clone';wrongOwner=case=='owner';enabled=case~='disabled';ownerID=case=='hero'and 0 or 4
 assert(not R.prepareWorldVAction(case=='foreign'and foreignV or summon,case=='action'and 0 or 28,manager))
 assert(writes==2,'unrelated actor or action modified')
end
assert(R.worldVActionPrepares==1 and not R.worldVActionError)
''')
print('PASS: checkpoint standby rejects native action; preparation admits action before dispatch, preserves bit128 and native return; foreign/inactive/clone/other actions untouched')
