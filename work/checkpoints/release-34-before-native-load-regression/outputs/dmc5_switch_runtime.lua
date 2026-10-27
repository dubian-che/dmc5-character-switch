-- Shared state for one PlayerManager update. No file I/O during normal play.
if _G.dmc5_switch_runtime then return _G.dmc5_switch_runtime end
local R={}
_G.dmc5_switch_runtime=R
function R.invalidate() R.cached=nil;R.scope=nil end
function R.withInputProfile(gm,id,fn)
 -- PlayingID is also used by native IsVergilMode. It must never retain
 -- a reserve actor's ID after the synchronous input refresh.
 local previous=gm:get_field('PlayingID')
 assert(type(previous)=='number','Native input identity unavailable')
 gm:set_field('PlayingID',id)
 local ok,result=pcall(fn)
 gm:set_field('PlayingID',previous)
 if not ok then error(result)end
 return result
end
function R.begin(manager) R.invalidate();R.pending=nil;R.updating=true;if manager then R.manager=manager end end
function R.permits(manager)
 manager=manager or R.manager;if not manager then return false end
 local active=manager:call('get_manualPlayer')
 local id=active and active:call('get_playerID')
 local allowed=false;local nativeID
 if id==0 or id==1 or id==4 then
  local gm=sdk.get_managed_singleton('app.GameManager')
  nativeID=gm and gm:call('findManualPlayerID')
  allowed=nativeID==0 or nativeID==1 or nativeID==4
 end
 if R.updating then R.scope={manager=manager,active=active,allowed=allowed,nativeID=nativeID}end
 return allowed
end
function R.afterUpdate(fn)
 if R.updating then R.pending=R.pending or {};R.pending[#R.pending+1]=fn else fn()end
end
function R.finish()
 local pending=R.pending;R.pending=nil;R.updating=false;R.invalidate()
 if pending then
  for _,fn in ipairs(pending)do
   local ok,why=pcall(fn)
   if not ok then R.error=tostring(why)end
  end
 end
end
function R.get(manager)
 if R.cached and R.cached.manager==manager then return R.cached end
 local c={manager=manager,active=manager:call('get_manualPlayer')}
 c.id=c.active and c.active:call('get_playerID') or -1
 c.gm=sdk.get_managed_singleton('app.GameManager')
 c.menuPaused=c.gm and (c.gm:call('get_isPauseMenu') or c.gm:call('get_isShopPause')) or false
 c.paused=not c.gm or c.menuPaused or c.gm:call('get_isPause')
 R.cached=c;return c
end
function R.delta(c)
 if c.dt~=nil then return c.dt end
 c.dt=0
 if not c.active or c.paused then return 0 end
 local hit=c.active:call('get_cachedHitController')
 local work=hit and hit:get_field('<cachedWorkRate>k__BackingField')
 local dt=work and work:call('getRateDeltaSec') or 0
 if dt>0 and dt<=0.25 then c.dt=dt end
 return c.dt
end
sdk.hook(sdk.find_type_definition('app.PlayerManager'):get_method('doUpdate'),function(args)R.begin(sdk.to_managed_object(args[2]))end,function(ret)R.finish();return ret end)
return R
