#pragma once

#include "numpad_streamdeck/core/key_config.hpp"

#include <string>
#include <unordered_map>
#include <vector>

namespace numpad_streamdeck::profiles {

struct Page {
    std::string name;
    std::unordered_map<std::string, core::KeyConfig> keys;
};

struct Profile {
    std::string name;
    std::vector<Page> pages;
};

class ProfileManager {
public:
    bool add(Profile profile);
    bool replace(Profile profile);
    bool remove(const std::string& name);
    bool select(const std::string& name);
    bool selectPage(std::size_t index);
    bool nextPage();
    bool previousPage();

    Profile* current();
    const Profile* current() const;
    const std::vector<Profile>& profiles() const;
    Page* currentPage();
    const Page* currentPage() const;
    std::size_t currentPageIndex() const;

private:
    std::vector<Profile> profiles_;
    std::string currentProfile_;
    std::size_t currentPage_ = 0;
};

} // namespace numpad_streamdeck::profiles