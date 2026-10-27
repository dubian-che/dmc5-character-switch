bool TestFramework::legacy_initialize() {
    if (m_wnd == 0) {
        return false;
    }

    if (m_first_frame || m_message_hook_requested || m_windows_message_hook == nullptr) {
        m_last_message_time = std::chrono::steady_clock::now();
        m_windows_message_hook.reset();
        m_windows_message_hook = std::make_unique<WindowsMessageHook>(m_wnd);
        m_windows_message_hook->on_message = [this](auto wnd, auto msg, auto w_param, auto l_param) {
            return on_message(wnd, msg, w_param, l_param);
        };

        m_message_hook_requested = false;
        return true;
    }

    m_message_hook_requested = false;
    return false;
}

bool TestFramework::initialize() {
    if (m_wnd == 0) {
        return false;
    }

    if (m_first_frame || m_message_hook_requested || m_windows_message_hook == nullptr) {
        m_last_message_time = std::chrono::steady_clock::now();
        // Keep the original forwarding link while this window registration
        // exists. Rewrapping an external subclass can create RF -> external -> RF.
        if (m_windows_message_hook != nullptr && m_windows_message_hook->is_valid_for(m_wnd)) {
            m_message_hook_requested = false;
            return true;
        }
        m_windows_message_hook.reset();
        m_windows_message_hook = std::make_unique<WindowsMessageHook>(m_wnd);
        m_windows_message_hook->on_message = [this](auto wnd, auto msg, auto w_param, auto l_param) {
            return on_message(wnd, msg, w_param, l_param);
        };

        m_message_hook_requested = false;
        return true;
    }

    m_message_hook_requested = false;
    return false;
}

