#include <stdio.h>
extern "C" {
#include "lua/lua.h"
#include "lua/lauxlib.h"
#include "lua/lualib.h"
}
int main(){
 for(int i=0;i<30;i++){
  lua_State* L=luaL_newstate();luaL_openlibs(L);
  const char* script="local f,e=package.loadlib('build/dmc5_keyboard.dll','dmc5_keyboard_poll');assert(f,e); for i=1,100 do for _,k in ipairs({9,116,117,118,119,120,121,0,255,-1,'bad'}) do local a,b=f(k);assert(type(a)=='boolean' and type(b)=='boolean'); if not a then assert(not b)end end end";
  if(luaL_dostring(L,script)){fprintf(stderr,"%s\n",lua_tostring(L,-1));return 1;}lua_close(L);
 }
 puts("PASS: native DLL load/unload across 30 Lua states, typed results, invalid keys and foreground gating.");return 0;
}
