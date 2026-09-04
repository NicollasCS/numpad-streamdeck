#pragma once

#include "numpad_streamdeck/actions/action.hpp"

#include <memory>
#include <string>
#include <unordered_map>

namespace numpad_streamdeck::actions {

class ActionManager {
public:
    void registerAction(std::string id, std::unique_ptr<Action> action);
    bool execute(const core::ActionReference& reference, const ActionContext& context, std::string& error) const;
    void clear();

private:
    std::unordered_map<std::string, std::unique_ptr<Action>> actions_;
};

} // namespace numpad_streamdeck::actions