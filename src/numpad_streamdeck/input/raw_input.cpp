#include "numpad_streamdeck/input/raw_input.hpp"

#include <chrono>
#include <string>

#ifdef Q_OS_WIN
#include <windows.h>
#include <hidusage.h>
#endif

namespace numpad_streamdeck::input {

RawInput::RawInput(QObject* parent) : QObject(parent) {}

bool RawInput::start() {
#ifdef Q_OS_WIN
    RAWINPUTDEVICE device{};
    device.usUsagePage = HID_USAGE_PAGE_GENERIC;
    device.usUsage = HID_USAGE_GENERIC_KEYBOARD;
    device.dwFlags = RIDEV_INPUTSINK | RIDEV_NOLEGACY;
    if (!RegisterRawInputDevices(&device, 1, sizeof(device))) {
        emit errorOccurred(QStringLiteral("RegisterRawInputDevices failed (%1)").arg(GetLastError()));
        return false;
    }
    registered_ = true;
    return true;
#else
    emit errorOccurred(QStringLiteral("Raw Input is only available on Windows"));
    return false;
#endif
}

void RawInput::stop() {
#ifdef Q_OS_WIN
    if (registered_) {
        RAWINPUTDEVICE device{};
        device.usUsagePage = HID_USAGE_PAGE_GENERIC;
        device.usUsage = HID_USAGE_GENERIC_KEYBOARD;
        device.dwFlags = RIDEV_REMOVE;
        RegisterRawInputDevices(&device, 1, sizeof(RAWINPUTDEVICE));
    }
#endif
    registered_ = false;
}

bool RawInput::nativeEventFilter(const QByteArray& eventType, void* message, qintptr* result) {
#ifdef Q_OS_WIN
    if (eventType != "windows_generic_MSG" && eventType != "windows_dispatcher_MSG") {
        return false;
    }
    auto* msg = static_cast<MSG*>(message);
    if (msg->message != WM_INPUT) {
        return false;
    }
    UINT size = 0;
    if (GetRawInputData(reinterpret_cast<HRAWINPUT>(msg->lParam), RID_INPUT, nullptr, &size,
                        sizeof(RAWINPUTHEADER)) == static_cast<UINT>(-1)) {
        return false;
    }
    QByteArray buffer(static_cast<qsizetype>(size), Qt::Uninitialized);
    if (GetRawInputData(reinterpret_cast<HRAWINPUT>(msg->lParam), RID_INPUT, buffer.data(), &size,
                        sizeof(RAWINPUTHEADER)) == static_cast<UINT>(-1)) {
        return false;
    }
    const auto* raw = reinterpret_cast<const RAWINPUT*>(buffer.constData());
    if (raw->header.dwType != RIM_TYPEKEYBOARD) {
        return false;
    }
    const auto& keyboard = raw->data.keyboard;
    const auto timestamp = std::chrono::steady_clock::now();
    emit keyEventReceived({std::string("vk:") + std::to_string(keyboard.VKey),
                           (keyboard.Flags & RI_KEY_BREAK) == 0, timestamp});
    if (result) {
        *result = 0;
    }
    return true;
#else
    Q_UNUSED(eventType)
    Q_UNUSED(message)
    Q_UNUSED(result)
    return false;
#endif
}

} // namespace numpad_streamdeck::input