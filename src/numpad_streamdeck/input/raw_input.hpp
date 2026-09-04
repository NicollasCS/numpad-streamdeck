#pragma once

#include "numpad_streamdeck/core/gesture_detector.hpp"

#include <QObject>
#include <QAbstractNativeEventFilter>
#include <QMetaType>

namespace numpad_streamdeck::input {

class RawInput final : public QObject, public QAbstractNativeEventFilter {
    Q_OBJECT
public:
    explicit RawInput(QObject* parent = nullptr);

    bool start();
    void stop();
    bool nativeEventFilter(const QByteArray& eventType, void* message, qintptr* result) override;

signals:
    void keyEventReceived(numpad_streamdeck::core::KeyEvent event);
    void errorOccurred(const QString& message);

private:
    bool registered_ = false;
};

} // namespace numpad_streamdeck::input

Q_DECLARE_METATYPE(numpad_streamdeck::core::KeyEvent)