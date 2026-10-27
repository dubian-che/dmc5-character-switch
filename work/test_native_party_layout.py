import sys
from pathlib import Path
sys.path.insert(0,'work/python-deps')
from lupa import LuaRuntime
from lua_test_support import install_module_loader
lua=LuaRuntime()
install_module_loader(lua)
lua.execute('''
sdk={hook=function()end,find_type_definition=function()return {get_method=function()end}end}
Vector3f={new=function(x,y,z)return {x=x,y=y,z=z}end}
dmc5_party_hud={nativeHooked=true,entries={}}
local function node()
 return {writes=0,call=function(self,n,v)
 self.writes=self.writes+1
 if n=='set_Position'then self.pos=v elseif n=='set_Scale'then self.scale=v elseif n=='set_Size'then self.size=v elseif n=='get_Size'then return self.size or {w=0,h=0}end
 end}
end
for i,id in ipairs({0,1,4})do
 dmc5_party_hud.entries[id]={id=id,index=i-1,zoom=0,all=node(),portrait=node(),hud={get_field=function()return nil end}}
end
''')
lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_party_hud.lua').read_text())
lua.execute('''
local H=dmc5_party_hud
for _,id in ipairs({0,1,4,1,0,4})do
 H.active=id
 local before=H.entries[id].y
 H.layout()
 if before and before~=35 then assert(H.entries[id].y~=35,'transition teleported')end
 for frame=1,180 do
  H.layout()
  for _,e in pairs(H.entries)do
   local s=e.all.scale
   -- A tilted 3D segment must retain the same aspect throughout the roll,
   -- not just after the selected row returns to full size.
   local length=math.sqrt((3*s.x)^2+(4*s.y)^2+(12*s.z)^2)
   assert(math.abs(length-13*s.x)<.00001,'3D HUD geometry distorted during transition')
   assert(s.x>=.32 and s.x<=1,'HUD overscaled')
  end
 end
 assert(H.entries[id].all.scale.x>0.9999,'active scale not native')
 assert(H.entries[id].y==35,'active not top')
 local ys={}
 for pid,e in pairs(H.entries)do
  if pid~=id then assert(math.abs(e.all.scale.x-.32)<0.0001);assert(e.y>35)end
  assert(not ys[e.y],'rows overlap after settling');ys[e.y]=true
 end
end
''')
lua.execute('''
local H=dmc5_party_hud
local writes=0
for _,e in pairs(H.entries)do writes=writes+e.all.writes end
for frame=1,600 do H.layout()end
local after=0
for _,e in pairs(H.entries)do after=after+e.all.writes end
assert(after==writes,'settled HUD still performs native writes')
H.paused=true;H.layout()
local pausedWrites=0
for _,e in pairs(H.entries)do pausedWrites=pausedWrites+e.all.writes end
assert(pausedWrites==writes+3,'pause must change visibility once per row')
for frame=1,60 do H.layout()end
local final=0
for _,e in pairs(H.entries)do final=final+e.all.writes end
assert(final==pausedWrites,'paused HUD repeats visibility writes')
''')
print('PASS: six selections; native active scale; undistorted 3D transitions; distinct rows; 600 settled frames do zero writes; pause visibility changes once.')
