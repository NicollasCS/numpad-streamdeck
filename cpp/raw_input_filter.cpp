#define UNICODE
#include <windows.h>
#include <hidusage.h>
#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <sstream>
#include <iomanip>

struct DeviceInfo {
    HANDLE handle = nullptr;
    std::wstring name;
};

static std::wstring GetDeviceNameFromHandle(HANDLE hDevice) {
    UINT size = 0;
    if (GetRawInputDeviceInfoW(hDevice, RIDI_DEVICENAME, nullptr, &size) == static_cast<UINT>(-1)) {
        return L"";
    }

    std::wstring name(size, L'\0');
    if (GetRawInputDeviceInfoW(hDevice, RIDI_DEVICENAME, &name[0], &size) == static_cast<UINT>(-1)) {
        return L"";
    }

    if (!name.empty() && name.back() == L'\0') {
        name.pop_back();
    }
    return name;
}

static std::vector<DeviceInfo> EnumerateKeyboards() {
    UINT count = 0;
    UINT result = GetRawInputDeviceList(nullptr, &count, sizeof(RAWINPUTDEVICELIST));
    if (result == static_cast<UINT>(-1) || count == 0) {
        return {};
    }

    std::vector<RAWINPUTDEVICELIST> devices(count);
    UINT actual = GetRawInputDeviceList(devices.data(), &count, sizeof(RAWINPUTDEVICELIST));
    if (actual == static_cast<UINT>(-1)) {
        return {};
    }

    std::vector<DeviceInfo> keyboards;
    for (UINT i = 0; i < actual; ++i) {
        if (devices[i].dwType != RIM_TYPEKEYBOARD) {
            continue;
        }

        DeviceInfo info;
        info.handle = devices[i].hDevice;
        info.name = GetDeviceNameFromHandle(info.handle);
        if (info.name.empty()) {
            std::wstringstream ss;
            ss << L"Keyboard-" << reinterpret_cast<uintptr_t>(info.handle);
            info.name = ss.str();
        }
        keyboards.push_back(info);
    }
    return keyboards;
}

static std::wstring ToHexPointer(HANDLE value) {
    std::wstringstream ss;
    ss << L"0x" << std::hex << reinterpret_cast<uintptr_t>(value);
    return ss.str();
}

static std::wstring NormalizeSelectedHandle(const std::wstring& value) {
    std::wstring v = value;
    if (v.empty()) return L"";
    std::wstring lowered;
    for (wchar_t ch : v) {
        lowered.push_back(static_cast<wchar_t>(towlower(ch)));
    }
    return lowered;
}

static std::wstring ToJsonString(const std::wstring& value) {
    std::wstring out;
    out.reserve(value.size() + 4);
    for (wchar_t ch : value) {
        switch (ch) {
            case L'\\': out += L"\\\\"; break;
            case L'"': out += L"\\\""; break;
            case L'\n': out += L"\\n"; break;
            case L'\r': out += L"\\r"; break;
            case L'\t': out += L"\\t"; break;
            default: out.push_back(ch); break;
        }
    }
    return out;
}

static std::wstring GetKeyNameFromVk(USHORT vk) {
    switch (vk) {
        case 0x08: return L"backspace";
        case 0x09: return L"tab";
        case 0x0D: return L"enter";
        case 0x10: return L"shift";
        case 0x11: return L"ctrl";
        case 0x12: return L"alt";
        case 0x14: return L"caps lock";
        case 0x20: return L"space";
        case 0x2E: return L"del";
        case 0x30: return L"0";
        case 0x31: return L"1";
        case 0x32: return L"2";
        case 0x33: return L"3";
        case 0x34: return L"4";
        case 0x35: return L"5";
        case 0x36: return L"6";
        case 0x37: return L"7";
        case 0x38: return L"8";
        case 0x39: return L"9";
        case 0x60: return L"0";
        case 0x61: return L"1";
        case 0x62: return L"2";
        case 0x63: return L"3";
        case 0x64: return L"4";
        case 0x65: return L"5";
        case 0x66: return L"6";
        case 0x67: return L"7";
        case 0x68: return L"8";
        case 0x69: return L"9";
        case 0x41: return L"a";
        case 0x42: return L"b";
        case 0x43: return L"c";
        case 0x44: return L"d";
        case 0x45: return L"e";
        case 0x46: return L"f";
        case 0x47: return L"g";
        case 0x48: return L"h";
        case 0x49: return L"i";
        case 0x4A: return L"j";
        case 0x4B: return L"k";
        case 0x4C: return L"l";
        case 0x4D: return L"m";
        case 0x4E: return L"n";
        case 0x4F: return L"o";
        case 0x50: return L"p";
        case 0x51: return L"q";
        case 0x52: return L"r";
        case 0x53: return L"s";
        case 0x54: return L"t";
        case 0x55: return L"u";
        case 0x56: return L"v";
        case 0x57: return L"w";
        case 0x58: return L"x";
        case 0x59: return L"y";
        case 0x5A: return L"z";
        case 0x6A: return L"*";
        case 0x6B: return L"+";
        case 0x6D: return L"-";
        case 0x6E: return L".";
        case 0x6F: return L"/";
        default: return L"key-" + std::to_wstring(vk);
    }
}

static std::wstring g_selected_filter = L"";

static bool ShouldProcessDevice(HANDLE selectedHandle, HANDLE currentHandle) {
    if (selectedHandle == nullptr) {
        return true;
    }
    return selectedHandle == currentHandle;
}

static LRESULT CALLBACK RawInputWndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    if (msg == WM_INPUT) {
        UINT dwSize = 0;
        if (GetRawInputData(reinterpret_cast<HRAWINPUT>(lParam), RID_INPUT, nullptr, &dwSize, sizeof(RAWINPUTHEADER)) == static_cast<UINT>(-1)) {
            return 0;
        }

        std::vector<BYTE> buffer(dwSize);
        if (GetRawInputData(reinterpret_cast<HRAWINPUT>(lParam), RID_INPUT, buffer.data(), &dwSize, sizeof(RAWINPUTHEADER)) == static_cast<UINT>(-1)) {
            return 0;
        }

        RAWINPUT* raw = reinterpret_cast<RAWINPUT*>(buffer.data());
        if (raw->header.dwType != RIM_TYPEKEYBOARD) {
            return 0;
        }

        HANDLE hDevice = raw->header.hDevice;
        std::wstring deviceName = GetDeviceNameFromHandle(hDevice);
        if (deviceName.empty()) {
            deviceName = L"Keyboard-" + ToHexPointer(hDevice);
        }

        std::wstring normalizedFilter = NormalizeSelectedHandle(g_selected_filter);
        std::wstring normalizedDeviceName = NormalizeSelectedHandle(deviceName);
        std::wstring normalizedHandleText = NormalizeSelectedHandle(ToHexPointer(hDevice));

        bool filterMatches = normalizedFilter.empty() ||
            normalizedDeviceName.find(normalizedFilter) != std::wstring::npos ||
            normalizedHandleText.find(normalizedFilter) != std::wstring::npos;

        if (!filterMatches) {
            return 0;
        }

        USHORT vk = raw->data.keyboard.VKey;
        USHORT flags = raw->data.keyboard.Flags;
        bool pressed = !(flags & RI_KEY_BREAK);

        std::wstring keyName = GetKeyNameFromVk(vk);
        std::wcout << L"{\"device\":\"" << ToJsonString(deviceName)
                   << L"\",\"handle\":\"" << ToJsonString(ToHexPointer(hDevice))
                   << L"\",\"vk\":" << vk
                   << L",\"name\":\"" << ToJsonString(keyName)
                   << L"\",\"pressed\":" << (pressed ? L"true" : L"false") << L"}\n";
        std::wcout.flush();

        return 0;
    }

    return DefWindowProcW(hwnd, msg, wParam, lParam);
}

static HWND CreateMessageWindow(HINSTANCE hInstance) {
    const wchar_t* className = L"NumpadRawInputClass";
    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(WNDCLASSEXW);
    wc.lpfnWndProc = RawInputWndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = className;

    ATOM atom = RegisterClassExW(&wc);
    if (!atom) {
        std::wcerr << L"RegisterClassExW failed" << std::endl;
        return nullptr;
    }

    HWND hwnd = CreateWindowExW(
        0,
        className,
        L"NumpadRawInputWindow",
        0,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        1,
        1,
        HWND_MESSAGE,
        nullptr,
        hInstance,
        nullptr
    );

    if (!hwnd) {
        std::wcerr << L"CreateWindowExW failed" << std::endl;
        return nullptr;
    }

    return hwnd;
}

static void RegisterKeyboardInput(HWND hwnd) {
    RAWINPUTDEVICE rid{};
    rid.usUsagePage = 0x01;
    rid.usUsage = 0x06;
    rid.dwFlags = RIDEV_INPUTSINK | RIDEV_NOLEGACY;
    rid.hwndTarget = hwnd;

    if (!RegisterRawInputDevices(&rid, 1, sizeof(rid))) {
        throw std::runtime_error("RegisterRawInputDevices failed");
    }
}

static void PrintUsage() {
    std::cout << "Usage:\n";
    std::cout << "  raw_input_filter.exe --list\n";
    std::cout << "  raw_input_filter.exe --test <device-handle-hex-or-name>\n";
    std::cout << "  raw_input_filter.exe --listen\n";
}

int wmain(int argc, wchar_t* argv[]) {
    if (argc < 2) {
        PrintUsage();
        return 1;
    }

    std::wstring mode = argv[1];

    if (mode == L"--list") {
        auto devices = EnumerateKeyboards();
        if (devices.empty()) {
            std::wcout << L"No keyboard devices found." << std::endl;
            return 0;
        }

        int index = 0;
        for (const auto& device : devices) {
            std::wcout << L"[" << index++ << L"] handle=" << ToHexPointer(device.handle) << L" name=" << device.name << L"\n";
        }
        return 0;
    }

    HINSTANCE hInstance = GetModuleHandleW(nullptr);
    HWND hwnd = CreateMessageWindow(hInstance);
    if (!hwnd) {
        return 1;
    }

    try {
        RegisterKeyboardInput(hwnd);
    } catch (const std::exception& ex) {
        std::cerr << ex.what() << std::endl;
        DestroyWindow(hwnd);
        return 1;
    }

    if (mode == L"--listen") {
        std::wcout << L"Listening for keyboard input. Press Ctrl+C in the console to stop." << std::endl;
        MSG msg{};
        while (GetMessageW(&msg, nullptr, 0, 0)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        return 0;
    }

    if (mode == L"--test") {
        if (argc < 3) {
            std::wcerr << L"Missing device filter" << std::endl;
            DestroyWindow(hwnd);
            return 1;
        }

        g_selected_filter = argv[2];
        std::wcout << L"Testing keyboard filter for: " << g_selected_filter << std::endl;

        MSG msg{};
        while (GetMessageW(&msg, nullptr, 0, 0)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        return 0;
    }

    PrintUsage();
    DestroyWindow(hwnd);
    return 1;
}
