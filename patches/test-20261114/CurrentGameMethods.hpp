#pragma once
#include <optional>
#include <initializer_list>
#include <windows.h>
#include <sdk/RETypeDB.hpp>
#include <sdk/RETypeDefinition.hpp>

namespace compat {
// Whole-method detours only. Interior assembly detours still require a full
// instruction/register/field audit and must not use this resolver.
inline std::optional<uintptr_t> checked_method(HMODULE module, const char* type, const char* signature,
    const char* return_type, std::initializer_list<const char*> params = {}) {
    auto method = sdk::find_method_definition(type, signature);
    if (!method || method->is_static() || method->get_num_params() != params.size()) return std::nullopt;
    const auto actual_params = method->get_param_types();
    if (actual_params.size() != params.size()) return std::nullopt;
    size_t index = 0;
    for (auto expected : params) {
        const auto actual = actual_params[index++];
        if (!actual || actual->get_full_name() != expected) return std::nullopt;
    }
    auto result = method->get_return_type();
    if (!result || result->get_full_name() != return_type) return std::nullopt;
    const auto address = reinterpret_cast<uintptr_t>(method->get_function());
    const auto base = reinterpret_cast<uintptr_t>(module);
    auto dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(module);
    if (!module || dos->e_magic != IMAGE_DOS_SIGNATURE) return std::nullopt;
    auto nt = reinterpret_cast<const IMAGE_NT_HEADERS*>(base + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE || address < base || address-base >= nt->OptionalHeader.SizeOfImage) return std::nullopt;
    MEMORY_BASIC_INFORMATION memory{};
    if (!VirtualQuery(reinterpret_cast<void*>(address), &memory, sizeof(memory))) return std::nullopt;
    if (memory.State != MEM_COMMIT || (memory.Protect & (PAGE_GUARD|PAGE_NOACCESS)) ||
        !(memory.Protect & (PAGE_EXECUTE|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY))) return std::nullopt;
    return address;
}
inline std::optional<uintptr_t> void_method(HMODULE module, const char* type, const char* signature,
    std::initializer_list<const char*> params = {}) {
    return checked_method(module, type, signature, "System.Void", params);
}
// Search adjacent ranges whose unwind chain reaches the entry through verified ranges.
// Do not infer ownership from adjacency alone or match across range boundaries.
inline std::optional<uintptr_t> unique_bytes_in_method(HMODULE module, uintptr_t entry,
    std::initializer_list<unsigned char> bytes) {
    if (!entry || bytes.size() == 0) return std::nullopt;
    DWORD64 image = 0;
    const auto root = RtlLookupFunctionEntry(entry, &image, nullptr);
    if (!root || image != reinterpret_cast<uintptr_t>(module) || entry != image + root->BeginAddress)
        return std::nullopt;
    auto range = root;
    RUNTIME_FUNCTION verified[32]{};
    std::optional<uintptr_t> found;
    for (unsigned count = 0; count < 32; ++count) {
        verified[count] = *range;
        const auto begin = image + range->BeginAddress;
        const auto end = image + range->EndAddress;
        if (end <= begin) return std::nullopt;
        if (bytes.size() <= end - begin) {
            for (auto at = begin; at <= end - bytes.size(); ++at) {
                size_t i = 0;
                for (auto byte : bytes) {
                    if (*reinterpret_cast<const unsigned char*>(at + i) != byte) break;
                    ++i;
                }
                if (i == bytes.size()) {
                    if (found) return std::nullopt;
                    found = at;
                }
            }
        }
        DWORD64 next_image = 0;
        const auto next = RtlLookupFunctionEntry(end, &next_image, nullptr);
        if (!next || next_image != image || next->BeginAddress != range->EndAddress) return found;
        const auto unwind = reinterpret_cast<const unsigned char*>(image + next->UnwindData);
        if ((unwind[0] & 7) != 1 || (unwind[0] >> 3) != UNW_FLAG_CHAININFO) return found;
        const auto chain = reinterpret_cast<const RUNTIME_FUNCTION*>(unwind + 4 + ((unwind[2] + 1) & ~1u) * 2);
        bool belongs = false;
        for (unsigned i = 0; i <= count; ++i) {
            const auto& prior = verified[i];
            if (chain->BeginAddress == prior.BeginAddress && chain->EndAddress == prior.EndAddress &&
                chain->UnwindData == prior.UnwindData) { belongs = true; break; }
        }
        if (!belongs) return found;
        range = next;
    }
    return std::nullopt; // Unexpected chain length: do not use a partial result.
}
}