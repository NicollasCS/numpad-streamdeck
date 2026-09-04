#include "numpad_streamdeck/core/gesture_detector.hpp"

#include <algorithm>
#include <utility>

namespace numpad_streamdeck::core {

GestureDetector::GestureDetector(GestureSettings settings) : settings_(settings) {}

void GestureDetector::setEnabled(bool enabled) {
    enabled_ = enabled;
    if (!enabled_) {
        states_.clear();
    }
}

void GestureDetector::setSettings(GestureSettings settings) {
    settings_ = settings;
}

void GestureDetector::setActionCallback(ActionCallback callback) {
    callback_ = std::move(callback);
}

void GestureDetector::registerKey(const KeyConfig& config) {
    configs_[config.keyId] = config;
}

void GestureDetector::removeKey(const std::string& keyId) {
    configs_.erase(keyId);
    states_.erase(keyId);
}

void GestureDetector::handleEvent(const KeyEvent& event) {
    if (!enabled_ || !configs_.contains(event.keyId)) {
        return;
    }

    auto& state = states_[event.keyId];
    if (event.pressed) {
        if (state.pressed) {
            return;
        }
        state.pressed = true;
        state.pressedAt = event.timestamp;
        const auto& config = configs_.at(event.keyId);
        state.repeated = config.repeatWhileHeld && hasGesture(config, GestureType::QuickPress) &&
            !hasGesture(config, GestureType::Hold) && !hasGesture(config, GestureType::DoublePress) &&
            !hasGesture(config, GestureType::TriplePress);
        if (state.repeated) {
            emit(event.keyId, GestureType::QuickPress);
        }
        return;
    }

    if (!state.pressed) {
        return;
    }
    state.pressed = false;
    state.repeated = false;
    const auto config = configs_.find(event.keyId);
    const auto pressDuration = elapsedSince(state.pressedAt, event.timestamp);
    if (config != configs_.end() && config->second.actions.contains(GestureType::Hold) &&
        pressDuration && pressDuration->count() >= settings_.holdThresholdMs) {
        emit(event.keyId, GestureType::Hold);
        state.tapCount = 0;
        return;
    }

    ++state.tapCount;
    state.lastReleasedAt = event.timestamp;
    if (state.tapCount >= 3) {
        emit(event.keyId, GestureType::TriplePress);
        state.tapCount = 0;
    }
}

void GestureDetector::flush(const std::chrono::steady_clock::time_point& now) {
    for (auto& [keyId, state] : states_) {
        if (state.pressed && state.repeated) {
            const auto elapsed = elapsedSince(state.pressedAt, now);
            if (elapsed && elapsed->count() >= 50) {
                state.pressedAt = now;
                emit(keyId, GestureType::QuickPress);
            }
            continue;
        }
        if (state.pressed || state.tapCount == 0) {
            continue;
        }
        const auto threshold = state.tapCount == 1
            ? settings_.doublePressThresholdMs
            : settings_.triplePressThresholdMs;
        const auto elapsed = elapsedSince(state.lastReleasedAt, now);
        if (elapsed && elapsed->count() >= threshold) {
            emitPending(keyId);
        }
    }
}

bool GestureDetector::hasGesture(const KeyConfig& config, GestureType gesture) const {
    const auto action = config.actions.find(gesture);
    return action != config.actions.end() && action->second.type != ActionType::None;
}

void GestureDetector::emit(const std::string& keyId, GestureType gesture) {
    const auto config = configs_.find(keyId);
    if (config == configs_.end() || !callback_) {
        return;
    }
    const auto action = config->second.actions.find(gesture);
    if (action != config->second.actions.end() && action->second.type != ActionType::None) {
        callback_(keyId, gesture, action->second);
    }
}

void GestureDetector::emitPending(const std::string& keyId) {
    auto& state = states_[keyId];
    emit(keyId, state.tapCount == 1 ? GestureType::QuickPress : GestureType::DoublePress);
    state.tapCount = 0;
}

std::optional<std::chrono::milliseconds> GestureDetector::elapsedSince(
    std::chrono::steady_clock::time_point start,
    std::chrono::steady_clock::time_point end) const {
    if (end < start) {
        return std::nullopt;
    }
    return std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
}

} // namespace numpad_streamdeck::core