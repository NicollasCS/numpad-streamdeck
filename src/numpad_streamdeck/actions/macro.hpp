#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace numpad_streamdeck::actions {

enum class MacroStepType { PressKey, ReleaseKey, Shortcut, TypeText, MouseClick, Wait };

struct MacroStep {
    MacroStepType type = MacroStepType::Wait;
    std::string value;
    std::int64_t delayMs = 0;
};

struct Macro {
    std::vector<MacroStep> steps;
};

} // namespace numpad_streamdeck::actions