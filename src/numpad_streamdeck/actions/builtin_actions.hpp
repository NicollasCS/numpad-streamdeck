#pragma once

#include "numpad_streamdeck/actions/action.hpp"
#include "numpad_streamdeck/actions/action_manager.hpp"

namespace numpad_streamdeck::actions {

class BuiltinAction final : public Action {
public:
    BuiltinAction(core::ActionType type, std::string id, std::string value = {});
    core::ActionType type() const override;
    bool execute(const ActionContext& context, std::string& error) override;

private:
    core::ActionType type_;
    std::string id_;
    std::string value_;
};

void registerBuiltinActions(ActionManager& manager);

} // namespace numpad_streamdeck::actions