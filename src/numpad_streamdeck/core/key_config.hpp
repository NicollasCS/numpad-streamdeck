#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>

namespace numpad_streamdeck::core {

enum class GestureType {
    QuickPress,
    Hold,
    DoublePress,
    TriplePress
};

enum class ActionType {
    None,
    Keyboard,
    Mouse,
    Media,
    Application,
    System,
    Macro
};

struct ActionReference {
    ActionType type = ActionType::None;
    std::string id;
    std::string value;
};

struct KeyConfig {
    std::string keyId;
    std::string name;
    std::string icon;
    bool toggle = false;
    bool repeatWhileHeld = true;
    std::unordered_map<GestureType, ActionReference> actions;
};

struct GestureSettings {
    std::int64_t holdThresholdMs = 500;
    std::int64_t doublePressThresholdMs = 400;
    std::int64_t triplePressThresholdMs = 400;
};

} // namespace numpad_streamdeck::core