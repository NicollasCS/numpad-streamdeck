#include "numpad_streamdeck/storage/json_storage.hpp"
#include "numpad_streamdeck/actions/macro.hpp"

#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QString>

#include <optional>
#include <utility>

namespace numpad_streamdeck::storage {

namespace {

QString actionTypeToString(core::ActionType type) {
    switch (type) {
    case core::ActionType::Keyboard: return QStringLiteral("keyboard");
    case core::ActionType::Mouse: return QStringLiteral("mouse");
    case core::ActionType::Media: return QStringLiteral("media");
    case core::ActionType::Application: return QStringLiteral("application");
    case core::ActionType::System: return QStringLiteral("system");
    case core::ActionType::Macro: return QStringLiteral("macro");
    case core::ActionType::None: return QStringLiteral("none");
    }
    return QStringLiteral("none");
}

core::ActionType actionTypeFromString(const QString& value) {
    if (value == QStringLiteral("keyboard")) return core::ActionType::Keyboard;
    if (value == QStringLiteral("mouse")) return core::ActionType::Mouse;
    if (value == QStringLiteral("media")) return core::ActionType::Media;
    if (value == QStringLiteral("application")) return core::ActionType::Application;
    if (value == QStringLiteral("system")) return core::ActionType::System;
    if (value == QStringLiteral("macro")) return core::ActionType::Macro;
    return core::ActionType::None;
}

QString gestureToString(core::GestureType gesture) {
    switch (gesture) {
    case core::GestureType::QuickPress: return QStringLiteral("quick_press");
    case core::GestureType::Hold: return QStringLiteral("hold");
    case core::GestureType::DoublePress: return QStringLiteral("double_press");
    case core::GestureType::TriplePress: return QStringLiteral("triple_press");
    }
    return QStringLiteral("quick_press");
}

std::optional<core::GestureType> gestureFromString(const QString& value) {
    if (value == QStringLiteral("quick_press")) return core::GestureType::QuickPress;
    if (value == QStringLiteral("hold")) return core::GestureType::Hold;
    if (value == QStringLiteral("double_press")) return core::GestureType::DoublePress;
    if (value == QStringLiteral("triple_press")) return core::GestureType::TriplePress;
    return std::nullopt;
}

QJsonObject keyToJson(const core::KeyConfig& key) {
    QJsonObject result{{QStringLiteral("keyId"), QString::fromStdString(key.keyId)},
                       {QStringLiteral("name"), QString::fromStdString(key.name)},
                       {QStringLiteral("icon"), QString::fromStdString(key.icon)},
                       {QStringLiteral("toggle"), key.toggle},
                       {QStringLiteral("repeatWhileHeld"), key.repeatWhileHeld}};
    QJsonObject actions;
    for (const auto& [gesture, action] : key.actions) {
        actions.insert(gestureToString(gesture), QJsonObject{
            {QStringLiteral("type"), actionTypeToString(action.type)},
            {QStringLiteral("id"), QString::fromStdString(action.id)},
            {QStringLiteral("value"), QString::fromStdString(action.value)}});
    }
    result.insert(QStringLiteral("actions"), actions);
    return result;
}

} // namespace

bool JsonStorage::saveProfile(const profiles::Profile& profile, const std::string& path, std::string& error) const {
    QJsonArray pages;
    for (const auto& page : profile.pages) {
        QJsonArray keys;
        for (const auto& [keyId, key] : page.keys) {
            Q_UNUSED(keyId)
            keys.append(keyToJson(key));
        }
        pages.append(QJsonObject{{QStringLiteral("name"), QString::fromStdString(page.name)},
                                 {QStringLiteral("keys"), keys}});
    }
    const QJsonObject root{{QStringLiteral("schemaVersion"), schemaVersion},
                           {QStringLiteral("name"), QString::fromStdString(profile.name)},
                           {QStringLiteral("pages"), pages}};
    QFile file(QString::fromStdString(path));
    if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
        error = file.errorString().toStdString();
        return false;
    }
    file.write(QJsonDocument(root).toJson(QJsonDocument::Indented));
    return true;
}

bool JsonStorage::loadProfile(const std::string& path, profiles::Profile& profile, std::string& error) const {
    QFile file(QString::fromStdString(path));
    if (!file.open(QIODevice::ReadOnly)) {
        error = file.errorString().toStdString();
        return false;
    }
    QJsonParseError parseError;
    const auto document = QJsonDocument::fromJson(file.readAll(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
        error = parseError.errorString().toStdString();
        return false;
    }
    const auto root = document.object();
    if (root.value(QStringLiteral("schemaVersion")).toInt() != schemaVersion) {
        error = "Unsupported profile schema version";
        return false;
    }
    profiles::Profile loaded;
    loaded.name = root.value(QStringLiteral("name")).toString().toStdString();
    for (const auto pageValue : root.value(QStringLiteral("pages")).toArray()) {
        const auto pageObject = pageValue.toObject();
        profiles::Page page;
        page.name = pageObject.value(QStringLiteral("name")).toString().toStdString();
        for (const auto keyValue : pageObject.value(QStringLiteral("keys")).toArray()) {
            const auto keyObject = keyValue.toObject();
            core::KeyConfig key;
            key.keyId = keyObject.value(QStringLiteral("keyId")).toString().toStdString();
            key.name = keyObject.value(QStringLiteral("name")).toString().toStdString();
            key.icon = keyObject.value(QStringLiteral("icon")).toString().toStdString();
            key.toggle = keyObject.value(QStringLiteral("toggle")).toBool();
            key.repeatWhileHeld = keyObject.value(QStringLiteral("repeatWhileHeld")).toBool(true);
            const auto actionObject = keyObject.value(QStringLiteral("actions")).toObject();
            for (auto iterator = actionObject.begin(); iterator != actionObject.end(); ++iterator) {
                const auto gesture = gestureFromString(iterator.key());
                if (!gesture || !iterator.value().isObject()) continue;
                const auto action = iterator.value().toObject();
                key.actions[*gesture] = {actionTypeFromString(action.value(QStringLiteral("type")).toString()),
                                         action.value(QStringLiteral("id")).toString().toStdString(),
                                         action.value(QStringLiteral("value")).toString().toStdString()};
            }
            if (!key.keyId.empty()) page.keys[key.keyId] = std::move(key);
        }
        loaded.pages.push_back(std::move(page));
    }
    if (loaded.name.empty() || loaded.pages.empty()) {
        error = "Profile must contain a name and at least one page";
        return false;
    }
    profile = std::move(loaded);
    return true;
}

} // namespace numpad_streamdeck::storage