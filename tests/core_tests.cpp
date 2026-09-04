#include "numpad_streamdeck/core/gesture_detector.hpp"
#include "numpad_streamdeck/actions/action_manager.hpp"
#include "numpad_streamdeck/actions/macro.hpp"
#include "numpad_streamdeck/profiles/profile.hpp"

#include <memory>
#include <string>

#include <cassert>
#include <chrono>
#include <vector>

using namespace numpad_streamdeck::core;
using Clock = std::chrono::steady_clock;

class TestAction final : public numpad_streamdeck::actions::Action {
public:
    explicit TestAction(bool& executed) : executed_(executed) {}
    ActionType type() const override { return ActionType::Media; }
    bool execute(const numpad_streamdeck::actions::ActionContext&, std::string&) override {
        executed_ = true;
        return true;
    }
private:
    bool& executed_;
};

int main() {
    const auto start = Clock::time_point{};
    GestureDetector detector({500, 400, 400});
    KeyConfig config;
    config.keyId = "keyboard::kp0";
    config.actions[GestureType::QuickPress] = {ActionType::Media, "play_pause"};
    config.actions[GestureType::Hold] = {ActionType::Application, "spotify"};
    config.actions[GestureType::DoublePress] = {ActionType::System, "show_desktop"};
    config.repeatWhileHeld = false;
    detector.registerKey(config);

    std::vector<GestureType> emitted;
    detector.setActionCallback([&](const std::string&, GestureType gesture, const ActionReference&) {
        emitted.push_back(gesture);
    });

    detector.handleEvent({config.keyId, true, start});
    detector.handleEvent({config.keyId, false, start + std::chrono::milliseconds(100)});
    detector.flush(start + std::chrono::milliseconds(501));
    assert(emitted == std::vector<GestureType>{GestureType::QuickPress});

    emitted.clear();
    detector.handleEvent({config.keyId, true, start + std::chrono::seconds(2)});
    detector.handleEvent({config.keyId, false, start + std::chrono::seconds(2) + std::chrono::milliseconds(100)});
    detector.handleEvent({config.keyId, true, start + std::chrono::seconds(2) + std::chrono::milliseconds(200)});
    detector.handleEvent({config.keyId, false, start + std::chrono::seconds(2) + std::chrono::milliseconds(300)});
    detector.flush(start + std::chrono::seconds(2) + std::chrono::milliseconds(701));
    assert(emitted == std::vector<GestureType>{GestureType::DoublePress});

    emitted.clear();
    detector.handleEvent({config.keyId, true, start + std::chrono::seconds(4)});
    detector.handleEvent({config.keyId, false, start + std::chrono::seconds(4) + std::chrono::milliseconds(600)});
    assert(emitted == std::vector<GestureType>{GestureType::Hold});

    emitted.clear();
    detector.setEnabled(false);
    detector.handleEvent({config.keyId, true, start + std::chrono::seconds(6)});
    detector.handleEvent({config.keyId, false, start + std::chrono::seconds(6) + std::chrono::milliseconds(100)});
    detector.flush(start + std::chrono::seconds(7));
    assert(emitted.empty());

    numpad_streamdeck::profiles::ProfileManager profiles;
    assert(profiles.add({"Default", {{"Main", {}}}}));
    assert(profiles.add({"Gaming", {{"Vehicle", {}}}}));
    assert(!profiles.add({"Gaming", {{"Duplicate", {}}}}));
    assert(profiles.current()->name == "Default");
    assert(profiles.select("Gaming"));
    assert(profiles.currentPage()->name == "Vehicle");
    assert(!profiles.nextPage());
    assert(!profiles.previousPage());
    assert(!profiles.remove("Default"));
    assert(profiles.remove("Gaming"));
    assert(profiles.current()->name == "Default");

    bool executed = false;
    numpad_streamdeck::actions::ActionManager actions;
    actions.registerAction("play", std::make_unique<TestAction>(executed));
    std::string error;
    assert(actions.execute({ActionType::Media, "play"}, {}, error));
    assert(executed);
    assert(!actions.execute({ActionType::System, "play"}, {}, error));

    numpad_streamdeck::actions::Macro macro{{
        {numpad_streamdeck::actions::MacroStepType::Shortcut, "ctrl+s", 0},
        {numpad_streamdeck::actions::MacroStepType::Wait, {}, 100}}};
    assert(macro.steps.size() == 2);
}