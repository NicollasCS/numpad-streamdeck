#pragma once

#include "numpad_streamdeck/core/key_config.hpp"

#include <string>

namespace numpad_streamdeck::actions {

struct ActionContext {
    bool toggleState = false;
    std::string value;
};

class Action {
public:
    virtual ~Action() = default;
    virtual core::ActionType type() const = 0;
    virtual bool execute(const ActionContext& context, std::string& error) = 0;
};

} // namespace numpad_streamdeck::actions