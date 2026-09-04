#pragma once

#include "numpad_streamdeck/profiles/profile.hpp"

#include <string>

namespace numpad_streamdeck::storage {

class JsonStorage {
public:
    static constexpr int schemaVersion = 1;

    bool saveProfile(const profiles::Profile& profile, const std::string& path, std::string& error) const;
    bool loadProfile(const std::string& path, profiles::Profile& profile, std::string& error) const;
};

} // namespace numpad_streamdeck::storage