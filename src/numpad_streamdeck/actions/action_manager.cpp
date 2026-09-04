#include "numpad_streamdeck/actions/action_manager.hpp"

#include <utility>

namespace numpad_streamdeck::actions {

void ActionManager::registerAction(std::string id, std::unique_ptr<Action> action) {
    if (!id.empty() && action) {
        actions_[std::move(id)] = std::move(action);
    }
}

bool ActionManager::execute(const core::ActionReference& reference, const ActionContext& context, std::string& error) const {
    if (reference.type == core::ActionType::None) {
        return true;
    }
    const auto iterator = actions_.find(reference.id);
    if (iterator == actions_.end() || iterator->second->type() != reference.type) {
        error = "Configured action is unavailable";
        return false;
    }
    auto executionContext = context;
    executionContext.value = reference.value;
    return iterator->second->execute(executionContext, error);
}

void ActionManager::clear() {
    actions_.clear();
}

} // namespace numpad_streamdeck::actions