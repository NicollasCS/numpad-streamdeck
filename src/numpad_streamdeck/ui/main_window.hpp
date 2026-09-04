#pragma once

#include "numpad_streamdeck/actions/action_manager.hpp"
#include "numpad_streamdeck/core/gesture_detector.hpp"
#include "numpad_streamdeck/input/raw_input.hpp"
#include "numpad_streamdeck/profiles/profile.hpp"
#include "numpad_streamdeck/storage/json_storage.hpp"

#include <QMainWindow>
#include <QTimer>

class QListWidget;
class QLabel;
class QGridLayout;
class QCheckBox;
class QSystemTrayIcon;
class QLineEdit;
class QComboBox;
class QPushButton;
class QTabWidget;
class QSpinBox;
class QWidget;
class QStackedWidget;

namespace numpad_streamdeck::ui {

class MainWindow final : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget* parent = nullptr);

private slots:
    void handleKeyEvent(core::KeyEvent event);
    void updateEnabled(bool enabled);
    void showProfile(int row);
    void restoreFromTray();
    void editKey(const QString& keyId);
    void saveKey();
    void deleteKey();
    void chooseEmptyKey();
    void changePage(int index);
    void nextPage();
    void openSettings();
    void previousPage();
    void deleteProfile();
    void cancelEdit();

private:
    void buildUi();
    void buildUiExact();
    void rebuildGrid();
    void addProfile();
    void clearEditor();
    void openSettingsPage();
    void saveCurrentProfile();
    QString profilePath() const;

    profiles::ProfileManager profiles_;
    actions::ActionManager actions_;
    input::RawInput rawInput_;
    core::GestureDetector gestures_;
    storage::JsonStorage storage_;
    QListWidget* profileList_ = nullptr;
    QGridLayout* keyGrid_ = nullptr;
    QLabel* statusLabel_ = nullptr;
    QCheckBox* enabledBox_ = nullptr;
    QSystemTrayIcon* tray_ = nullptr;
    QLineEdit* keyIdEdit_ = nullptr;
    QLineEdit* nameEdit_ = nullptr;
    QLineEdit* iconEdit_ = nullptr;
    QLineEdit* valueEdit_ = nullptr;
    QComboBox* actionCombo_ = nullptr;
    QComboBox* gestureCombo_ = nullptr;
    QCheckBox* toggleEdit_ = nullptr;
    QCheckBox* repeatEdit_ = nullptr;
    QPushButton* saveButton_ = nullptr;
    QPushButton* deleteButton_ = nullptr;
    QPushButton* cancelButton_ = nullptr;
    QString editingKeyId_;
    QComboBox* pageCombo_ = nullptr;
    QWidget* editor_ = nullptr;
    bool waitingForKey_ = false;
    QTimer repeatTimer_;
    QTabWidget* tabs_ = nullptr;
    QStackedWidget* contentStack_ = nullptr;
    QSpinBox* holdSetting_ = nullptr;
    QSpinBox* doubleSetting_ = nullptr;
    QSpinBox* tripleSetting_ = nullptr;
    QCheckBox* startupSetting_ = nullptr;
    QCheckBox* minimizeSetting_ = nullptr;
    QCheckBox* disableSetting_ = nullptr;

protected:
    void closeEvent(QCloseEvent* event) override;
};

} // namespace numpad_streamdeck::ui