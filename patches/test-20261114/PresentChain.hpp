#pragma once

// A later hook may already call our bootstrap entry. Do not insert ourselves
// above it again when moving to the instance vtable: that creates a cycle.
template <typename Fn>
constexpr bool present_chain_needs_entry(Fn current, Fn downstream, Fn self) {
    return current == downstream || current == self;
}
