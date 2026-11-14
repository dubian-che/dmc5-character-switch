#pragma once
#include <vector>
#include <MinHook.h>

// Stage gameplay hooks until every module has initialized successfully.
// Renderer/input hooks created outside this scope retain their old behavior.
class GameplayHookBatch {
public:
    GameplayHookBatch() { previous = current; current = this; }
    GameplayHookBatch(const GameplayHookBatch&) = delete;
    GameplayHookBatch& operator=(const GameplayHookBatch&) = delete;
    ~GameplayHookBatch() { current = previous; }

    static MH_STATUS enable(LPVOID target) {
        if (!current) return MH_EnableHook(target);
        current->targets.push_back(target);
        return MH_OK; // Created trampoline is valid, but game code is untouched.
    }
    bool commit() {
        for (auto target : targets) {
            if (MH_QueueEnableHook(target) != MH_OK) { cancel(); return false; }
        }
        if (MH_ApplyQueued() != MH_OK) { cancel(); return false; }
        targets.clear();
        current = previous;
        return true;
    }
private:
    void cancel() {
        for (auto target : targets) MH_QueueDisableHook(target);
        MH_ApplyQueued();
    }
    inline static thread_local GameplayHookBatch* current = nullptr;
    GameplayHookBatch* previous = nullptr;
    std::vector<LPVOID> targets;
};

