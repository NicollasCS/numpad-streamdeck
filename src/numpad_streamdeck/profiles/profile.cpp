#include "numpad_streamdeck/profiles/profile.hpp"

#include <algorithm>
#include <utility>

namespace numpad_streamdeck::profiles {

bool ProfileManager::add(Profile profile) {
    if (profile.name.empty() || profile.pages.empty() ||
        std::any_of(profiles_.begin(), profiles_.end(), [&](const Profile& item) {
            return item.name == profile.name;
        })) {
        return false;
    }
    profiles_.push_back(std::move(profile));
    if (currentProfile_.empty()) {
        currentProfile_ = profiles_.back().name;
    }
    return true;
}

bool ProfileManager::replace(Profile profile) {
    if (profile.name.empty() || profile.pages.empty()) {
        return false;
    }
    const auto iterator = std::find_if(profiles_.begin(), profiles_.end(), [&](const Profile& item) {
        return item.name == profile.name;
    });
    if (iterator == profiles_.end()) {
        profiles_.push_back(std::move(profile));
    } else {
        *iterator = std::move(profile);
    }
    if (currentProfile_.empty()) {
        currentProfile_ = profiles_.back().name;
    }
    return true;
}

bool ProfileManager::remove(const std::string& name) {
    if (name == "Default") {
        return false;
    }
    const auto iterator = std::find_if(profiles_.begin(), profiles_.end(), [&](const Profile& profile) {
        return profile.name == name;
    });
    if (iterator == profiles_.end()) {
        return false;
    }
    profiles_.erase(iterator);
    if (currentProfile_ == name) {
        currentProfile_ = profiles_.empty() ? std::string{} : profiles_.front().name;
        currentPage_ = 0;
    }
    return true;
}

bool ProfileManager::select(const std::string& name) {
    const auto exists = std::any_of(profiles_.begin(), profiles_.end(), [&](const Profile& profile) {
        return profile.name == name;
    });
    if (!exists) {
        return false;
    }
    currentProfile_ = name;
    currentPage_ = 0;
    return true;
}

bool ProfileManager::selectPage(std::size_t index) {
    const auto* profile = current();
    if (!profile || index >= profile->pages.size()) return false;
    currentPage_ = index;
    return true;
}

bool ProfileManager::nextPage() {
    const auto* profile = current();
    if (!profile || currentPage_ + 1 >= profile->pages.size()) return false;
    ++currentPage_;
    return true;
}

bool ProfileManager::previousPage() {
    if (currentPage_ == 0 || !current()) return false;
    --currentPage_;
    return true;
}

Profile* ProfileManager::current() {
    const auto iterator = std::find_if(profiles_.begin(), profiles_.end(), [&](const Profile& profile) {
        return profile.name == currentProfile_;
    });
    return iterator == profiles_.end() ? nullptr : &*iterator;
}

const Profile* ProfileManager::current() const {
    const auto iterator = std::find_if(profiles_.begin(), profiles_.end(), [&](const Profile& profile) {
        return profile.name == currentProfile_;
    });
    return iterator == profiles_.end() ? nullptr : &*iterator;
}

const std::vector<Profile>& ProfileManager::profiles() const {
    return profiles_;
}

Page* ProfileManager::currentPage() {
    auto* profile = current();
    if (profile == nullptr || currentPage_ >= profile->pages.size()) {
        return nullptr;
    }
    return &profile->pages[currentPage_];
}

const Page* ProfileManager::currentPage() const {
    const auto profile = current();
    if (profile == nullptr || currentPage_ >= profile->pages.size()) {
        return nullptr;
    }
    return &profile->pages[currentPage_];
}

std::size_t ProfileManager::currentPageIndex() const {
    return currentPage_;
}

} // namespace numpad_streamdeck::profiles