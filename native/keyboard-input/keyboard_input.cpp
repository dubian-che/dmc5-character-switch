#include <windows.h>
extern "C" {
#include "lua/lua.h"
}
// Lua 5.4.3 ABI, built from the exact dependency of the pinned REFramework.
// No hooks, worker thread, logging, key injection or game-memory writes.
extern "C" __declspec(dllexport) int dmc5_keyboard_poll(lua_State* L) {
    int valid=0;
    const lua_Integer key=lua_tointegerx(L,1,&valid);
    DWORD owner=0;
    HWND foreground=GetForegroundWindow();
    if (foreground) GetWindowThreadProcessId(foreground,&owner);
    const bool active=foreground && owner==GetCurrentProcessId();
    const bool down=active && valid && key>=8 && key<=254 &&
        (GetAsyncKeyState(static_cast<int>(key)) & 0x8000)!=0;
    lua_pushboolean(L,active);
    lua_pushboolean(L,down);
    return 2;
}
