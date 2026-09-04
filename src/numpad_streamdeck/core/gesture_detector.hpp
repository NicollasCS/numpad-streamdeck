#pragma once

#include "numpad_streamdeck/core/key_config.hpp"

#include <chrono>
#include <functional>
#include <optional>
#include <string>
#include <unordered_map>

namespace numpad_streamdeck::core {

struct KeyEvent {
    std::string keyId;
    bool pressed = false;
    std::chrono::steady_clock::time_point timestamp;
};

class GestureDetector {
public:
    using ActionCallback = std::function<void(const std::string&, GestureType, const ActionReference&)>;

    explicit GestureDetector(GestureSettings settings = {});

    void setEnabled(bool enabled);
    void setSettings(GestureSettings settings);
    void setActionCallback(ActionCallback callback);

    void registerKey(const KeyConfig& config);
    void removeKey(const std::string& keyId);
    void handleEvent(const KeyEvent& event);
    void flush(const std::chrono::steady_clock::time_point& now);

private:
    struct PressState {
        std::chrono::steady_clock::time_point pressedAt;
        std::chrono::steady_clock::time_point lastReleasedAt;
        int tapCount = 0;
        bool pressed = false;
        bool repeated = false;
    };

    void emit(const std::string& keyId, GestureType gesture);
    void emitPending(const std::string& keyId);
    std::optional<std::chrono::milliseconds> elapsedSince(
        std::chrono::steady_clock::time_point start,
        std::chrono::steady_clock::time_point end) const;
    bool hasGesture(const KeyConfig& config, GestureType gesture) const;

    GestureSettings settings_;
    bool enabled_ = true;
    ActionCallback callback_;
    std::unordered_map<std::string, KeyConfig> configs_;
    std::unordered_map<std::string, PressState> states_;
};

} // namespace numpad_streamdeck::core