#include "numpad_streamdeck/actions/builtin_actions.hpp"

#include "numpad_streamdeck/actions/action_manager.hpp"

#ifdef _WIN32
#include <windows.h>
#include <shellapi.h>
#include <shlobj.h>
#endif

#include <utility>
#include <array>
#include <filesystem>
#include <sstream>
#include <vector>

namespace numpad_streamdeck::actions {

BuiltinAction::BuiltinAction(core::ActionType type, std::string id, std::string value)
    : type_(type), id_(std::move(id)), value_(std::move(value)) {}

core::ActionType BuiltinAction::type() const {
    return type_;
}

bool BuiltinAction::execute(const ActionContext& context, std::string& error) {
#ifdef _WIN32
    const auto& value = context.value;
    if (type_ == core::ActionType::Keyboard && id_ == "type_text") {
        if (value.empty()) return true;
        std::vector<INPUT> inputs;
        inputs.reserve(value.size() * 2);
        for (const auto character : value) {
            INPUT press{};
            press.type = INPUT_KEYBOARD;
            press.ki.dwFlags = KEYEVENTF_UNICODE;
            press.ki.wScan = static_cast<WORD>(static_cast<unsigned char>(character));
            inputs.push_back(press);
            press.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP;
            inputs.push_back(press);
        }
        return SendInput(static_cast<UINT>(inputs.size()), inputs.data(), sizeof(INPUT)) == inputs.size();
    }
    if (type_ == core::ActionType::Keyboard && id_ == "keyboard_shortcut") {
        if (value.empty() || value.find_first_of("\r\n") != std::string::npos) {
            error = "Shortcut is empty or invalid";
            return false;
        }
        std::vector<WORD> keys;
        std::stringstream stream(value);
        std::string token;
        while (std::getline(stream, token, '+')) {
            while (!token.empty() && token.front() == ' ') token.erase(token.begin());
            while (!token.empty() && token.back() == ' ') token.pop_back();
            if (token == "ctrl") keys.push_back(VK_CONTROL);
            else if (token == "shift") keys.push_back(VK_SHIFT);
            else if (token == "alt") keys.push_back(VK_MENU);
            else if (token == "win") keys.push_back(VK_LWIN);
            else if (!token.empty()) {
                const auto virtualKey = VkKeyScanA(token.front());
                if (virtualKey == -1) { error = "Unsupported shortcut key"; return false; }
                keys.push_back(static_cast<WORD>(virtualKey & 0xff));
            }
        }
        if (keys.empty()) { error = "Shortcut is empty"; return false; }
        std::vector<INPUT> inputs;
        for (const auto key : keys) {
            INPUT input{}; input.type = INPUT_KEYBOARD; input.ki.wVk = key; inputs.push_back(input);
        }
        for (auto iterator = keys.rbegin(); iterator != keys.rend(); ++iterator) {
            INPUT input{}; input.type = INPUT_KEYBOARD; input.ki.wVk = *iterator; input.ki.dwFlags = KEYEVENTF_KEYUP; inputs.push_back(input);
        }
        return SendInput(static_cast<UINT>(inputs.size()), inputs.data(), sizeof(INPUT)) == inputs.size();
    }
    if (type_ == core::ActionType::Application && id_ == "open_folder") {
        if (value.empty() || !std::filesystem::is_directory(std::filesystem::path(value))) {
            error = "Folder does not exist";
            return false;
        }
        return reinterpret_cast<std::intptr_t>(ShellExecuteW(nullptr, L"open", std::filesystem::path(value).c_str(), nullptr, nullptr, SW_SHOWNORMAL)) > 32;
    }
    if (type_ == core::ActionType::System && id_ == "screenshot") {
        const auto desktop = std::filesystem::path(std::getenv("USERPROFILE") ? std::getenv("USERPROFILE") : ".") / "Desktop";
        std::filesystem::create_directories(desktop);
        const auto path = desktop / ("screenshot_" + std::to_string(GetTickCount64()) + ".bmp");
        const auto screen = GetDC(nullptr);
        const auto width = GetSystemMetrics(SM_CXSCREEN);
        const auto height = GetSystemMetrics(SM_CYSCREEN);
        const auto memory = CreateCompatibleDC(screen);
        const auto bitmap = CreateCompatibleBitmap(screen, width, height);
        const auto previous = SelectObject(memory, bitmap);
        BitBlt(memory, 0, 0, width, height, screen, 0, 0, SRCCOPY | CAPTUREBLT);
        BITMAPINFOHEADER header{};
        header.biSize = sizeof(header); header.biWidth = width; header.biHeight = -height;
        header.biPlanes = 1; header.biBitCount = 32; header.biCompression = BI_RGB;
        std::vector<std::byte> pixels(static_cast<std::size_t>(width) * height * 4);
        GetDIBits(memory, bitmap, 0, height, pixels.data(), reinterpret_cast<BITMAPINFO*>(&header), DIB_RGB_COLORS);
        BITMAPFILEHEADER fileHeader{};
        fileHeader.bfType = 0x4D42; fileHeader.bfOffBits = sizeof(fileHeader) + sizeof(header);
        fileHeader.bfSize = fileHeader.bfOffBits + static_cast<DWORD>(pixels.size());
        HANDLE file = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        DWORD written = 0;
        const bool saved = file != INVALID_HANDLE_VALUE &&
            WriteFile(file, &fileHeader, sizeof(fileHeader), &written, nullptr) &&
            WriteFile(file, &header, sizeof(header), &written, nullptr) &&
            WriteFile(file, pixels.data(), static_cast<DWORD>(pixels.size()), &written, nullptr);
        if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
        SelectObject(memory, previous); DeleteObject(bitmap); DeleteDC(memory); ReleaseDC(nullptr, screen);
        if (!saved) { error = "Could not save screenshot"; return false; }
        return true;
    }
    if (type_ == core::ActionType::Application) {
        if (value.empty()) {
            error = "Application or file path is empty";
            return false;
        }
        const auto path = std::filesystem::path(value);
        if (!std::filesystem::exists(path)) {
            error = "Application or file does not exist";
            return false;
        }
        return reinterpret_cast<std::intptr_t>(ShellExecuteW(nullptr, L"open", path.c_str(), nullptr, nullptr, SW_SHOWNORMAL)) > 32;
    }
    if (type_ == core::ActionType::System && id_ == "open_website") {
        if (value.empty() || value.find_first_of("\r\n") != std::string::npos) {
            error = "Invalid website URL";
            return false;
        }
        const auto url = value.starts_with("http://") || value.starts_with("https://") ? value : "https://" + value;
        return reinterpret_cast<std::intptr_t>(ShellExecuteA(nullptr, "open", url.c_str(), nullptr, nullptr, SW_SHOWNORMAL)) > 32;
    }
    if (type_ == core::ActionType::Mouse) {
        DWORD mouseFlags = 0;
        if (id_ == "left_click") mouseFlags = MOUSEEVENTF_LEFTDOWN | MOUSEEVENTF_LEFTUP;
        else if (id_ == "right_click") mouseFlags = MOUSEEVENTF_RIGHTDOWN | MOUSEEVENTF_RIGHTUP;
        else if (id_ == "middle_click") mouseFlags = MOUSEEVENTF_MIDDLEDOWN | MOUSEEVENTF_MIDDLEUP;
        else if (id_ == "scroll_up") mouseFlags = MOUSEEVENTF_WHEEL;
        else if (id_ == "scroll_down") mouseFlags = MOUSEEVENTF_WHEEL;
        else {
            error = "Unknown mouse action";
            return false;
        }
        INPUT input{};
        input.type = INPUT_MOUSE;
        input.mi.dwFlags = mouseFlags;
        input.mi.mouseData = id_ == "scroll_down" ? static_cast<DWORD>(-WHEEL_DELTA) :
            (id_ == "scroll_up" ? WHEEL_DELTA : 0);
        return SendInput(1, &input, sizeof(INPUT)) == 1;
    }
    if (type_ == core::ActionType::Keyboard) {
        if (id_ == "close_window") {
            const auto window = GetForegroundWindow();
            return window != nullptr && PostMessageW(window, WM_CLOSE, 0, 0) != 0;
        }
        std::array<INPUT, 4> inputs{};
        WORD modifier = 0;
        WORD key = 0;
        if (id_ == "alt_tab") { modifier = VK_MENU; key = VK_TAB; }
        else if (id_ == "win_tab") { modifier = VK_LWIN; key = VK_TAB; }
        else { error = "Unknown keyboard action"; return false; }
        inputs[0].type = INPUT_KEYBOARD;
        inputs[0].ki.wVk = modifier;
        inputs[1].type = INPUT_KEYBOARD;
        inputs[1].ki.wVk = key;
        inputs[2] = inputs[1];
        inputs[2].ki.dwFlags = KEYEVENTF_KEYUP;
        inputs[3] = inputs[0];
        inputs[3].ki.dwFlags = KEYEVENTF_KEYUP;
        return SendInput(static_cast<UINT>(inputs.size()), inputs.data(), sizeof(INPUT)) == inputs.size();
    }
    WORD virtualKey = 0;
    DWORD flags = KEYEVENTF_KEYUP;
    if (id_ == "play_pause") virtualKey = VK_MEDIA_PLAY_PAUSE;
    else if (id_ == "next_track") virtualKey = VK_MEDIA_NEXT_TRACK;
    else if (id_ == "prev_track") virtualKey = VK_MEDIA_PREV_TRACK;
    else if (id_ == "volume_up") virtualKey = VK_VOLUME_UP;
    else if (id_ == "volume_down") virtualKey = VK_VOLUME_DOWN;
    else if (id_ == "mute") virtualKey = VK_VOLUME_MUTE;
    else if (id_ == "show_desktop") virtualKey = VK_LWIN;
    else if (id_ == "task_manager") {
        ShellExecuteW(nullptr, L"open", L"taskmgr.exe", nullptr, nullptr, SW_SHOWNORMAL);
        return true;
    } else if (id_ == "lock_pc") {
        return LockWorkStation() != 0;
    } else {
        error = "Unknown built-in action";
        return false;
    }
    if (id_ == "show_desktop") {
        std::array<INPUT, 4> inputs{};
        inputs[0].type = INPUT_KEYBOARD;
        inputs[0].ki.wVk = VK_LWIN;
        inputs[1].type = INPUT_KEYBOARD;
        inputs[1].ki.wVk = 'D';
        inputs[2] = inputs[1];
        inputs[2].ki.dwFlags = flags;
        inputs[3] = inputs[0];
        inputs[3].ki.dwFlags = flags;
        return SendInput(static_cast<UINT>(inputs.size()), inputs.data(), sizeof(INPUT)) == inputs.size();
    }
    std::array<INPUT, 2> inputs{};
    inputs[0].type = INPUT_KEYBOARD;
    inputs[0].ki.wVk = virtualKey;
    inputs[1] = inputs[0];
    inputs[1].ki.dwFlags = flags;
    return SendInput(static_cast<UINT>(inputs.size()), inputs.data(), sizeof(INPUT)) == inputs.size();
#else
    error = "Built-in actions require Windows";
    return false;
#endif
}

void registerBuiltinActions(ActionManager& manager) {
    for (const auto& id : {"play_pause", "next_track", "prev_track", "volume_up", "volume_down", "mute"}) {
        manager.registerAction(id, std::make_unique<BuiltinAction>(core::ActionType::Media, id));
    }
    for (const auto& id : {"show_desktop", "task_manager", "lock_pc"}) {
        manager.registerAction(id, std::make_unique<BuiltinAction>(core::ActionType::System, id));
    }
    for (const auto& id : {"alt_tab", "win_tab", "close_window"}) {
        manager.registerAction(id, std::make_unique<BuiltinAction>(core::ActionType::Keyboard, id));
    }
    for (const auto& id : {"left_click", "right_click", "middle_click", "scroll_up", "scroll_down"}) {
        manager.registerAction(id, std::make_unique<BuiltinAction>(core::ActionType::Mouse, id));
    }
    manager.registerAction("open_application", std::make_unique<BuiltinAction>(core::ActionType::Application, "open_application"));
    manager.registerAction("open_file", std::make_unique<BuiltinAction>(core::ActionType::Application, "open_file"));
    manager.registerAction("open_folder", std::make_unique<BuiltinAction>(core::ActionType::Application, "open_folder"));
    manager.registerAction("open_website", std::make_unique<BuiltinAction>(core::ActionType::System, "open_website"));
    manager.registerAction("keyboard_shortcut", std::make_unique<BuiltinAction>(core::ActionType::Keyboard, "keyboard_shortcut"));
    manager.registerAction("type_text", std::make_unique<BuiltinAction>(core::ActionType::Keyboard, "type_text"));
    manager.registerAction("screenshot", std::make_unique<BuiltinAction>(core::ActionType::System, "screenshot"));
}

} // namespace numpad_streamdeck::actions