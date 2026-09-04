#include "numpad_streamdeck/ui/main_window.hpp"
#include "numpad_streamdeck/actions/builtin_actions.hpp"

#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QCloseEvent>
#include <QDir>
#include <QDialog>
#include <QFormLayout>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMessageBox>
#include <QPushButton>
#include <QSpinBox>
#include <QSystemTrayIcon>
#include <QStandardPaths>
#include <QSettings>
#include <QTabWidget>
#include <QStackedWidget>
#include <QMenu>
#include <QSplitter>
#include <QVBoxLayout>
#include <QWidget>
#include <QFile>

#include <utility>

namespace numpad_streamdeck::ui {

MainWindow::MainWindow(QWidget* parent) : QMainWindow(parent) {
    actions::registerBuiltinActions(actions_);
    profiles_.add({"Default", {{"Numpad", {}}}});
    profiles::Profile loadedProfile;
    std::string loadError;
    if (storage_.loadProfile(profilePath().toStdString(), loadedProfile, loadError)) {
        profiles_.replace(std::move(loadedProfile));
    }
    QSettings settings(QStringLiteral("NumpadStreamDeck"), QStringLiteral("NumpadStreamDeck"));
    gestures_.setSettings({settings.value(QStringLiteral("holdThresholdMs"), 500).toLongLong(),
                           settings.value(QStringLiteral("doublePressThresholdMs"), 400).toLongLong(),
                           settings.value(QStringLiteral("triplePressThresholdMs"), 400).toLongLong()});
    gestures_.setActionCallback([this](const std::string&, core::GestureType,
                                       const core::ActionReference& reference) {
        std::string error;
        actions_.execute(reference, {}, error);
    });
    connect(&rawInput_, &input::RawInput::keyEventReceived, this, &MainWindow::handleKeyEvent);
    repeatTimer_.setInterval(25);
    connect(&repeatTimer_, &QTimer::timeout, this, [this]() {
        gestures_.flush(std::chrono::steady_clock::now());
    });
    repeatTimer_.start();
    buildUiExact();
    if (QFile theme(QStringLiteral("resources/themes/default.qss")); theme.open(QIODevice::ReadOnly)) {
        qApp->setStyleSheet(QString::fromUtf8(theme.readAll()));
    }
    for (const auto& profile : profiles_.profiles()) {
        for (const auto& page : profile.pages) {
            for (const auto& [keyId, key] : page.keys) {
                Q_UNUSED(keyId)
                gestures_.registerKey(key);
            }
        }
    }
    tray_ = new QSystemTrayIcon(this);
    tray_->setIcon(windowIcon());
    auto* trayMenu = new QMenu(this);
    auto* restore = trayMenu->addAction(QStringLiteral("Open"));
    connect(restore, &QAction::triggered, this, &MainWindow::restoreFromTray);
    auto* trayEnabled = trayMenu->addAction(QStringLiteral("Enabled"));
    trayEnabled->setCheckable(true);
    trayEnabled->setChecked(true);
    connect(trayEnabled, &QAction::toggled, enabledBox_, &QCheckBox::setChecked);
    trayMenu->addSeparator();
    auto* exit = trayMenu->addAction(QStringLiteral("Exit"));
    connect(exit, &QAction::triggered, this, [this]() {
        tray_->hide();
        rawInput_.stop();
        qApp->exit(0);
    });
    tray_->setContextMenu(trayMenu);
    connect(tray_, &QSystemTrayIcon::activated, this, [this](QSystemTrayIcon::ActivationReason reason) {
        if (reason == QSystemTrayIcon::Trigger || reason == QSystemTrayIcon::DoubleClick) restoreFromTray();
    });
    tray_->show();
    qApp->installNativeEventFilter(&rawInput_);
    rawInput_.start();
}

void MainWindow::buildUi() {
    setWindowTitle(QStringLiteral("Numpad Stream Deck"));
    resize(1000, 700);
    auto* root = new QWidget(this);
    auto* rootLayout = new QVBoxLayout(root);
    tabs_ = new QTabWidget(root);
    rootLayout->addWidget(tabs_);
    auto* deckPage = new QWidget(tabs_);
    auto* layout = new QVBoxLayout(deckPage);
    auto* header = new QHBoxLayout();
    header->addWidget(new QLabel(QStringLiteral("Keyboard")));
    auto* keyboardCombo = new QComboBox(deckPage);
    keyboardCombo->addItem(QStringLiteral("Numpad - select device"));
    keyboardCombo->setMinimumWidth(300);
    header->addWidget(keyboardCombo, 1);
    auto* saveKeyboard = new QPushButton(QStringLiteral("Save"), deckPage);
    header->addWidget(saveKeyboard);
    header->addStretch();
    statusLabel_ = new QLabel(QStringLiteral("ENABLED"));
    enabledBox_ = new QCheckBox(QStringLiteral("Enabled"));
    enabledBox_->setChecked(true);
    connect(enabledBox_, &QCheckBox::toggled, this, &MainWindow::updateEnabled);
    header->addWidget(statusLabel_);
    header->addWidget(enabledBox_);
    layout->addLayout(header);

    auto* splitter = new QSplitter(Qt::Horizontal, root);
    auto* profilesPanel = new QWidget(splitter);
    auto* profilesLayout = new QVBoxLayout(profilesPanel);
    profilesLayout->addWidget(new QLabel(QStringLiteral("PROFILES")));
    profileList_ = new QListWidget(profilesPanel);
    for (const auto& profile : profiles_.profiles()) {
        profileList_->addItem(QString::fromStdString(profile.name));
    }
    profileList_->setCurrentRow(0);
    connect(profileList_, &QListWidget::currentRowChanged, this, &MainWindow::showProfile);
    profilesLayout->addWidget(profileList_);
    auto* newProfile = new QPushButton(QStringLiteral("+ New Profile"), profilesPanel);
    connect(newProfile, &QPushButton::clicked, this, &MainWindow::addProfile);
    profilesLayout->addWidget(newProfile);
    auto* removeProfile = new QPushButton(QStringLiteral("Delete Profile"), profilesPanel);
    connect(removeProfile, &QPushButton::clicked, this, &MainWindow::deleteProfile);
    profilesLayout->addWidget(removeProfile);
    splitter->addWidget(profilesPanel);

    auto* gridPanel = new QWidget(splitter);
    auto* gridPanelLayout = new QVBoxLayout(gridPanel);
    auto* pageBar = new QHBoxLayout();
    pageCombo_ = new QComboBox(gridPanel);
    auto* previousPageButton = new QPushButton(QStringLiteral("<"), gridPanel);
    auto* nextPageButton = new QPushButton(QStringLiteral(">"), gridPanel);
    pageBar->addWidget(previousPageButton);
    pageBar->addWidget(pageCombo_, 1);
    pageBar->addWidget(nextPageButton);
    gridPanelLayout->addLayout(pageBar);
    keyGrid_ = new QGridLayout();
    keyGrid_->setVerticalSpacing(12);
    gridPanelLayout->addLayout(keyGrid_);
    connect(pageCombo_, qOverload<int>(&QComboBox::currentIndexChanged), this, &MainWindow::changePage);
    connect(previousPageButton, &QPushButton::clicked, this, &MainWindow::previousPage);
    connect(nextPageButton, &QPushButton::clicked, this, &MainWindow::nextPage);
    splitter->addWidget(gridPanel);
    splitter->setStretchFactor(1, 1);
    layout->addWidget(splitter, 1);

    editor_ = new QWidget(root);
    auto* editor = editor_;
    auto* editorLayout = new QFormLayout(editor);
    editorLayout->addRow(new QLabel(QStringLiteral("EDIT KEY")));
    keyIdEdit_ = new QLineEdit(editor);
    nameEdit_ = new QLineEdit(editor);
    iconEdit_ = new QLineEdit(editor);
    actionCombo_ = new QComboBox(editor);
    actionCombo_->addItem(QStringLiteral("None"), QStringLiteral("none"));
    actionCombo_->addItem(QStringLiteral("Play / Pause"), QStringLiteral("play_pause"));
    actionCombo_->addItem(QStringLiteral("Next Track"), QStringLiteral("next_track"));
    actionCombo_->addItem(QStringLiteral("Previous Track"), QStringLiteral("prev_track"));
    actionCombo_->addItem(QStringLiteral("Volume Up"), QStringLiteral("volume_up"));
    actionCombo_->addItem(QStringLiteral("Volume Down"), QStringLiteral("volume_down"));
    actionCombo_->addItem(QStringLiteral("Mute"), QStringLiteral("mute"));
    actionCombo_->addItem(QStringLiteral("Show Desktop"), QStringLiteral("show_desktop"));
    actionCombo_->addItem(QStringLiteral("Task Manager"), QStringLiteral("task_manager"));
    actionCombo_->addItem(QStringLiteral("Lock PC"), QStringLiteral("lock_pc"));
    actionCombo_->addItem(QStringLiteral("Alt + Tab"), QStringLiteral("alt_tab"));
    actionCombo_->addItem(QStringLiteral("Win + Tab"), QStringLiteral("win_tab"));
    actionCombo_->addItem(QStringLiteral("Close Window"), QStringLiteral("close_window"));
    actionCombo_->addItem(QStringLiteral("Left Click"), QStringLiteral("left_click"));
    actionCombo_->addItem(QStringLiteral("Right Click"), QStringLiteral("right_click"));
    actionCombo_->addItem(QStringLiteral("Middle Click"), QStringLiteral("middle_click"));
    actionCombo_->addItem(QStringLiteral("Scroll Up"), QStringLiteral("scroll_up"));
    actionCombo_->addItem(QStringLiteral("Scroll Down"), QStringLiteral("scroll_down"));
    actionCombo_->addItem(QStringLiteral("Open Application"), QStringLiteral("open_application"));
    actionCombo_->addItem(QStringLiteral("Open File"), QStringLiteral("open_file"));
    actionCombo_->addItem(QStringLiteral("Open Folder"), QStringLiteral("open_folder"));
    actionCombo_->addItem(QStringLiteral("Open Website"), QStringLiteral("open_website"));
    actionCombo_->addItem(QStringLiteral("Keyboard Shortcut"), QStringLiteral("keyboard_shortcut"));
    actionCombo_->addItem(QStringLiteral("Type Text"), QStringLiteral("type_text"));
    actionCombo_->addItem(QStringLiteral("Screenshot"), QStringLiteral("screenshot"));
    connect(actionCombo_, qOverload<int>(&QComboBox::currentIndexChanged), this, [this](int) {
        valueEdit_->setVisible(actionCombo_->currentData().toString() == QStringLiteral("open_application") ||
                               actionCombo_->currentData().toString() == QStringLiteral("open_file") ||
                               actionCombo_->currentData().toString() == QStringLiteral("open_folder") ||
                               actionCombo_->currentData().toString() == QStringLiteral("open_website") ||
                               actionCombo_->currentData().toString() == QStringLiteral("keyboard_shortcut") ||
                               actionCombo_->currentData().toString() == QStringLiteral("type_text"));
    });
    gestureCombo_ = new QComboBox(editor);
    gestureCombo_->addItem(QStringLiteral("Quick Press"), static_cast<int>(core::GestureType::QuickPress));
    gestureCombo_->addItem(QStringLiteral("Hold"), static_cast<int>(core::GestureType::Hold));
    gestureCombo_->addItem(QStringLiteral("Double Press"), static_cast<int>(core::GestureType::DoublePress));
    gestureCombo_->addItem(QStringLiteral("Triple Press"), static_cast<int>(core::GestureType::TriplePress));
    toggleEdit_ = new QCheckBox(QStringLiteral("Toggle"), editor);
    repeatEdit_ = new QCheckBox(QStringLiteral("Repeat while held"), editor);
    repeatEdit_->setChecked(true);
    valueEdit_ = new QLineEdit(editor);
    valueEdit_->setPlaceholderText(QStringLiteral("Path, executable or URL"));
    valueEdit_->setVisible(false);
    keyIdEdit_->setVisible(false);
    editorLayout->addRow(QStringLiteral("Key"), new QLabel(QStringLiteral("Captured automatically"), editor));
    editorLayout->addRow(QStringLiteral("Name"), nameEdit_);
    editorLayout->addRow(QStringLiteral("Icon"), iconEdit_);
    editorLayout->addRow(QStringLiteral("Value"), valueEdit_);
    editorLayout->addRow(QStringLiteral("Action"), actionCombo_);
    editorLayout->addRow(QStringLiteral("Gesture"), gestureCombo_);
    editorLayout->addRow(QString(), toggleEdit_);
    editorLayout->addRow(QString(), repeatEdit_);
    auto* editorButtons = new QHBoxLayout();
    saveButton_ = new QPushButton(QStringLiteral("Save"), editor);
    deleteButton_ = new QPushButton(QStringLiteral("Delete"), editor);
    editorButtons->addWidget(deleteButton_);
    editorButtons->addStretch();
    editorButtons->addWidget(saveButton_);
    editorLayout->addRow(editorButtons);
    connect(saveButton_, &QPushButton::clicked, this, &MainWindow::saveKey);
    connect(deleteButton_, &QPushButton::clicked, this, &MainWindow::deleteKey);
    layout->addWidget(editor);
    tabs_->addTab(deckPage, QStringLiteral("HOME"));
    auto* settingsPage = new QWidget(tabs_);
    auto* settingsLayout = new QHBoxLayout(settingsPage);
    auto* settingsOptions = new QVBoxLayout();
    settingsOptions->addWidget(new QLabel(QStringLiteral("WINDOWS"), settingsPage));
    QSettings appSettings(QStringLiteral("NumpadStreamDeck"), QStringLiteral("NumpadStreamDeck"));
    holdSetting_ = new QSpinBox(settingsPage);
    holdSetting_->setRange(50, 5000);
    holdSetting_->setValue(appSettings.value(QStringLiteral("holdThresholdMs"), 500).toInt());
    doubleSetting_ = new QSpinBox(settingsPage);
    doubleSetting_->setRange(50, 2000);
    doubleSetting_->setValue(appSettings.value(QStringLiteral("doublePressThresholdMs"), 400).toInt());
    tripleSetting_ = new QSpinBox(settingsPage);
    tripleSetting_->setRange(50, 2000);
    tripleSetting_->setValue(appSettings.value(QStringLiteral("triplePressThresholdMs"), 400).toInt());
    auto* inputCard = new QWidget(settingsPage);
    auto* inputForm = new QFormLayout(inputCard);
    inputForm->addRow(QStringLiteral("Hold threshold (ms)"), holdSetting_);
    inputForm->addRow(QStringLiteral("Double press (ms)"), doubleSetting_);
    inputForm->addRow(QStringLiteral("Triple press (ms)"), tripleSetting_);
    settingsOptions->addWidget(inputCard);
    startupSetting_ = new QCheckBox(QStringLiteral("Start with Windows"), settingsPage);
    minimizeSetting_ = new QCheckBox(QStringLiteral("Minimize to tray when closing"), settingsPage);
    disableSetting_ = new QCheckBox(QStringLiteral("Disable Stream Deck"), settingsPage);
    startupSetting_->setChecked(appSettings.value(QStringLiteral("startWithWindows"), false).toBool());
    minimizeSetting_->setChecked(appSettings.value(QStringLiteral("minimizeToTray"), true).toBool());
    disableSetting_->setChecked(!enabledBox_->isChecked());
    settingsOptions->addWidget(startupSetting_);
    settingsOptions->addWidget(minimizeSetting_);
    settingsOptions->addWidget(disableSetting_);
    settingsOptions->addStretch();
    settingsLayout->addLayout(settingsOptions, 1);
    auto* keyboardOptions = new QVBoxLayout();
    auto* keyboardTitle = new QLabel(QStringLiteral("Keyboard"), settingsPage);
    keyboardOptions->addWidget(keyboardTitle);
    auto* settingsKeyboardCombo = new QComboBox(settingsPage);
    settingsKeyboardCombo->addItem(QStringLiteral("Numpad - select device"));
    keyboardOptions->addWidget(settingsKeyboardCombo);
    auto* renameKeyboard = new QLineEdit(settingsPage);
    renameKeyboard->setPlaceholderText(QStringLiteral("Rename keyboard"));
    keyboardOptions->addWidget(renameKeyboard);
    auto* testKey = new QPushButton(QStringLiteral("Test key"), settingsPage);
    keyboardOptions->addWidget(testKey);
    auto* keyboardInfo = new QHBoxLayout();
    keyboardInfo->addWidget(new QLabel(QStringLiteral("Keyboard"), settingsPage));
    keyboardInfo->addWidget(new QLabel(QStringLiteral("Key pressed"), settingsPage));
    keyboardOptions->addLayout(keyboardInfo);
    keyboardOptions->addStretch();
    settingsLayout->addLayout(keyboardOptions, 2);
    auto* saveSettings = new QPushButton(QStringLiteral("Save Settings"), settingsPage);
    keyboardOptions->addWidget(saveSettings);
    connect(saveSettings, &QPushButton::clicked, this, [this]() {
        gestures_.setSettings({holdSetting_->value(), doubleSetting_->value(), tripleSetting_->value()});
        QSettings settings(QStringLiteral("NumpadStreamDeck"), QStringLiteral("NumpadStreamDeck"));
        settings.setValue(QStringLiteral("holdThresholdMs"), holdSetting_->value());
        settings.setValue(QStringLiteral("doublePressThresholdMs"), doubleSetting_->value());
        settings.setValue(QStringLiteral("triplePressThresholdMs"), tripleSetting_->value());
        settings.setValue(QStringLiteral("startWithWindows"), startupSetting_->isChecked());
        settings.setValue(QStringLiteral("minimizeToTray"), minimizeSetting_->isChecked());
        enabledBox_->setChecked(!disableSetting_->isChecked());
    });
    tabs_->addTab(settingsPage, QStringLiteral("SETTINGS"));
    setCentralWidget(root);
    clearEditor();
    editor_->setVisible(false);
    rebuildGrid();
}

void MainWindow::buildUiExact() {
    setWindowTitle(QStringLiteral("Numpad Stream Deck"));
    resize(1180, 760);

    auto* root = new QWidget(this);
    auto* rootLayout = new QHBoxLayout(root);
    rootLayout->setContentsMargins(0, 0, 0, 0);
    rootLayout->setSpacing(0);

    auto* sidebarStack = new QStackedWidget(root);
    sidebarStack->setFixedWidth(300);
    auto* homeSidebar = new QWidget(sidebarStack);
    auto* homeSidebarLayout = new QVBoxLayout(homeSidebar);
    homeSidebarLayout->setContentsMargins(18, 22, 18, 18);
    auto* presetsTitle = new QLabel(QStringLiteral("PRESETS"), homeSidebar);
    presetsTitle->setObjectName(QStringLiteral("sidebarTitle"));
    homeSidebarLayout->addWidget(presetsTitle);
    profileList_ = new QListWidget(homeSidebar);
    for (const auto& profile : profiles_.profiles()) profileList_->addItem(QString::fromStdString(profile.name));
    connect(profileList_, &QListWidget::currentRowChanged, this, &MainWindow::showProfile);
    homeSidebarLayout->addWidget(profileList_, 1);
    auto* newProfile = new QPushButton(QStringLiteral("New Profile"), homeSidebar);
    auto* deleteProfile = new QPushButton(QStringLiteral("Delete Profile"), homeSidebar);
    connect(newProfile, &QPushButton::clicked, this, &MainWindow::addProfile);
    connect(deleteProfile, &QPushButton::clicked, this, &MainWindow::deleteProfile);
    homeSidebarLayout->addWidget(newProfile);
    homeSidebarLayout->addWidget(deleteProfile);
    sidebarStack->addWidget(homeSidebar);

    auto* settingsSidebar = new QWidget(sidebarStack);
    auto* settingsSidebarLayout = new QVBoxLayout(settingsSidebar);
    settingsSidebarLayout->setContentsMargins(18, 22, 18, 18);
    auto* windowsTitle = new QLabel(QStringLiteral("WINDOWS"), settingsSidebar);
    windowsTitle->setObjectName(QStringLiteral("sidebarTitle"));
    settingsSidebarLayout->addWidget(windowsTitle);
    QSettings saved(QStringLiteral("NumpadStreamDeck"), QStringLiteral("NumpadStreamDeck"));
    startupSetting_ = new QCheckBox(QStringLiteral("Start with Windows"), settingsSidebar);
    minimizeSetting_ = new QCheckBox(QStringLiteral("Start with Windows in the tray"), settingsSidebar);
    auto* closeToTray = new QCheckBox(QStringLiteral("Minimize to tray when closing"), settingsSidebar);
    disableSetting_ = new QCheckBox(QStringLiteral("Disable StreamDeck"), settingsSidebar);
    startupSetting_->setChecked(saved.value(QStringLiteral("startWithWindows"), false).toBool());
    minimizeSetting_->setChecked(saved.value(QStringLiteral("startMinimized"), false).toBool());
    closeToTray->setChecked(saved.value(QStringLiteral("minimizeToTray"), true).toBool());
    disableSetting_->setChecked(false);
    settingsSidebarLayout->addWidget(startupSetting_);
    settingsSidebarLayout->addWidget(minimizeSetting_);
    settingsSidebarLayout->addWidget(closeToTray);
    settingsSidebarLayout->addWidget(disableSetting_);
    settingsSidebarLayout->addStretch();
    auto* version = new QLabel(QStringLiteral("version : release v3.0.0\ngithub.com/NicollasCS/numpad-streamdeck"), settingsSidebar);
    version->setObjectName(QStringLiteral("versionLabel"));
    settingsSidebarLayout->addWidget(version);
    sidebarStack->addWidget(settingsSidebar);
    rootLayout->addWidget(sidebarStack);

    auto* mainArea = new QWidget(root);
    auto* mainLayout = new QVBoxLayout(mainArea);
    mainLayout->setContentsMargins(18, 18, 22, 18);
    auto* navigation = new QHBoxLayout();
    auto* homeButton = new QPushButton(QStringLiteral("HOME"), mainArea);
    auto* settingsButton = new QPushButton(QStringLiteral("SETTINGS"), mainArea);
    homeButton->setObjectName(QStringLiteral("navButton"));
    settingsButton->setObjectName(QStringLiteral("navButton"));
    navigation->addWidget(homeButton);
    navigation->addWidget(settingsButton);
    statusLabel_ = new QLabel(QStringLiteral("ENABLED"), mainArea);
    enabledBox_ = new QCheckBox(QStringLiteral("Enabled"), mainArea);
    enabledBox_->setChecked(true);
    connect(enabledBox_, &QCheckBox::toggled, this, &MainWindow::updateEnabled);
    navigation->addStretch();
    navigation->addWidget(statusLabel_);
    navigation->addWidget(enabledBox_);
    mainLayout->addLayout(navigation);
    contentStack_ = new QStackedWidget(mainArea);
    mainLayout->addWidget(contentStack_, 1);

    auto* homePage = new QWidget(contentStack_);
    auto* homeLayout = new QVBoxLayout(homePage);
    homeLayout->setContentsMargins(8, 32, 0, 0);
    auto* keyboardRow = new QHBoxLayout();
    keyboardRow->addWidget(new QLabel(QStringLiteral("Keyboard"), homePage));
    auto* keyboard = new QComboBox(homePage);
    keyboard->addItem(QStringLiteral("Numpad - id ...................."));
    auto* dropdown = new QPushButton(QStringLiteral("V"), homePage);
    auto* saveKeyboard = new QPushButton(QStringLiteral("Save"), homePage);
    keyboardRow->addWidget(keyboard, 1);
    keyboardRow->addWidget(dropdown);
    keyboardRow->addWidget(saveKeyboard);
    homeLayout->addLayout(keyboardRow);
    auto* addFunction = new QPushButton(QStringLiteral("+ Add Function"), homePage);
    addFunction->setObjectName(QStringLiteral("primaryButton"));
    connect(addFunction, &QPushButton::clicked, this, &MainWindow::chooseEmptyKey);
    homeLayout->addWidget(addFunction);
    auto* pageBar = new QHBoxLayout();
    auto* previousPageButton = new QPushButton(QStringLiteral("<"), homePage);
    pageCombo_ = new QComboBox(homePage);
    auto* nextPageButton = new QPushButton(QStringLiteral(">"), homePage);
    pageBar->addWidget(previousPageButton);
    pageBar->addWidget(pageCombo_, 1);
    pageBar->addWidget(nextPageButton);
    homeLayout->addLayout(pageBar);
    connect(pageCombo_, qOverload<int>(&QComboBox::currentIndexChanged), this, &MainWindow::changePage);
    connect(previousPageButton, &QPushButton::clicked, this, &MainWindow::previousPage);
    connect(nextPageButton, &QPushButton::clicked, this, &MainWindow::nextPage);
    keyGrid_ = new QGridLayout();
    keyGrid_->setVerticalSpacing(12);
    homeLayout->addLayout(keyGrid_);
    editor_ = new QWidget(homePage);
    auto* editorLayout = new QFormLayout(editor_);
    keyIdEdit_ = new QLineEdit(editor_);
    nameEdit_ = new QLineEdit(editor_);
    iconEdit_ = new QLineEdit(editor_);
    valueEdit_ = new QLineEdit(editor_);
    actionCombo_ = new QComboBox(editor_);
    actionCombo_->addItem(QStringLiteral("None"), QStringLiteral("none"));
    for (const auto& item : {std::pair{QStringLiteral("Play / Pause"), QStringLiteral("play_pause")},
                             std::pair{QStringLiteral("Volume Up"), QStringLiteral("volume_up")},
                             std::pair{QStringLiteral("Volume Down"), QStringLiteral("volume_down")},
                             std::pair{QStringLiteral("Mute"), QStringLiteral("mute")},
                             std::pair{QStringLiteral("Keyboard Shortcut"), QStringLiteral("keyboard_shortcut")},
                             std::pair{QStringLiteral("Type Text"), QStringLiteral("type_text")},
                             std::pair{QStringLiteral("Open Application"), QStringLiteral("open_application")},
                             std::pair{QStringLiteral("Open File"), QStringLiteral("open_file")},
                             std::pair{QStringLiteral("Open Folder"), QStringLiteral("open_folder")},
                             std::pair{QStringLiteral("Open Website"), QStringLiteral("open_website")},
                             std::pair{QStringLiteral("Screenshot"), QStringLiteral("screenshot")}}) actionCombo_->addItem(item.first, item.second);
    gestureCombo_ = new QComboBox(editor_);
    gestureCombo_->addItem(QStringLiteral("Quick Press"), static_cast<int>(core::GestureType::QuickPress));
    gestureCombo_->addItem(QStringLiteral("Hold"), static_cast<int>(core::GestureType::Hold));
    gestureCombo_->addItem(QStringLiteral("Double Press"), static_cast<int>(core::GestureType::DoublePress));
    gestureCombo_->addItem(QStringLiteral("Triple Press"), static_cast<int>(core::GestureType::TriplePress));
    toggleEdit_ = new QCheckBox(QStringLiteral("Toggle"), editor_);
    repeatEdit_ = new QCheckBox(QStringLiteral("Repeat while held"), editor_);
    repeatEdit_->setChecked(true);
    editorLayout->addRow(QStringLiteral("Name"), nameEdit_);
    editorLayout->addRow(QStringLiteral("Icon"), iconEdit_);
    editorLayout->addRow(QStringLiteral("Value"), valueEdit_);
    editorLayout->addRow(QStringLiteral("Action"), actionCombo_);
    editorLayout->addRow(QStringLiteral("Gesture"), gestureCombo_);
    editorLayout->addRow(QString(), toggleEdit_);
    editorLayout->addRow(QString(), repeatEdit_);
    auto* editorButtons = new QHBoxLayout();
    saveButton_ = new QPushButton(QStringLiteral("Save"), editor_);
    deleteButton_ = new QPushButton(QStringLiteral("Delete"), editor_);
    cancelButton_ = new QPushButton(QStringLiteral("Cancel"), editor_);
    editorButtons->addWidget(deleteButton_);
    editorButtons->addWidget(cancelButton_);
    editorButtons->addStretch();
    editorButtons->addWidget(saveButton_);
    editorLayout->addRow(editorButtons);
    connect(saveButton_, &QPushButton::clicked, this, &MainWindow::saveKey);
    connect(deleteButton_, &QPushButton::clicked, this, &MainWindow::deleteKey);
    connect(cancelButton_, &QPushButton::clicked, this, &MainWindow::cancelEdit);
    connect(actionCombo_, qOverload<int>(&QComboBox::currentIndexChanged), this, [this](int) {
        const auto id = actionCombo_->currentData().toString();
        valueEdit_->setVisible(id == QStringLiteral("open_application") || id == QStringLiteral("open_file") ||
                               id == QStringLiteral("open_folder") || id == QStringLiteral("open_website") ||
                               id == QStringLiteral("keyboard_shortcut") || id == QStringLiteral("type_text"));
    });
    homeLayout->addWidget(editor_);
    editor_->setVisible(false);
    contentStack_->addWidget(homePage);

    auto* settingsPage = new QWidget(contentStack_);
    auto* settingsPageLayout = new QVBoxLayout(settingsPage);
    settingsPageLayout->setContentsMargins(8, 32, 0, 0);
    auto* settingsKeyboard = new QComboBox(settingsPage);
    settingsKeyboard->addItem(QStringLiteral("Keyboard                         V"));
    auto* renameKeyboard = new QLineEdit(settingsPage);
    renameKeyboard->setPlaceholderText(QStringLiteral("Rename keyboard"));
    auto* saveSettings = new QPushButton(QStringLiteral("Save"), settingsPage);
    auto* testKey = new QPushButton(QStringLiteral("Test key"), settingsPage);
    testKey->setMaximumWidth(260);
    settingsPageLayout->addWidget(settingsKeyboard);
    settingsPageLayout->addWidget(renameKeyboard);
    settingsPageLayout->addWidget(saveSettings, 0, Qt::AlignLeft);
    settingsPageLayout->addStretch(1);
    settingsPageLayout->addWidget(testKey, 0, Qt::AlignHCenter);
    auto* diagnostics = new QHBoxLayout();
    diagnostics->addWidget(new QLabel(QStringLiteral("Keyboard\n\nNumpad"), settingsPage));
    diagnostics->addWidget(new QLabel(QStringLiteral("Key pressed\n\nKey 145"), settingsPage));
    settingsPageLayout->addLayout(diagnostics);
    contentStack_->addWidget(settingsPage);

    connect(homeButton, &QPushButton::clicked, this, [sidebarStack, this]() {
        contentStack_->setCurrentIndex(0); sidebarStack->setCurrentIndex(0);
    });
    connect(settingsButton, &QPushButton::clicked, this, [sidebarStack, this]() {
        contentStack_->setCurrentIndex(1); sidebarStack->setCurrentIndex(1);
    });
    connect(saveSettings, &QPushButton::clicked, this, [this, closeToTray]() {
        QSettings settings(QStringLiteral("NumpadStreamDeck"), QStringLiteral("NumpadStreamDeck"));
        settings.setValue(QStringLiteral("holdThresholdMs"), holdSetting_->value());
        settings.setValue(QStringLiteral("doublePressThresholdMs"), doubleSetting_->value());
        settings.setValue(QStringLiteral("triplePressThresholdMs"), tripleSetting_->value());
        settings.setValue(QStringLiteral("startWithWindows"), startupSetting_->isChecked());
        settings.setValue(QStringLiteral("startMinimized"), minimizeSetting_->isChecked());
        settings.setValue(QStringLiteral("minimizeToTray"), closeToTray->isChecked());
        enabledBox_->setChecked(!disableSetting_->isChecked());
    });
    rootLayout->addWidget(mainArea, 1);
    setCentralWidget(root);
    rebuildGrid();
}

void MainWindow::rebuildGrid() {
    while (auto* item = keyGrid_->takeAt(0)) {
        delete item->widget();
        delete item;
    }
    const auto* page = profiles_.currentPage();
    if (!page) return;
    pageCombo_->blockSignals(true);
    pageCombo_->clear();
    for (const auto& item : profiles_.current()->pages) {
        pageCombo_->addItem(QString::fromStdString(item.name));
    }
    pageCombo_->setCurrentIndex(static_cast<int>(profiles_.currentPageIndex()));
    pageCombo_->blockSignals(false);
    int index = 0;
    for (const auto& [keyId, config] : page->keys) {
        auto* card = new QWidget();
        card->setObjectName(QStringLiteral("functionCard"));
        auto* cardLayout = new QVBoxLayout(card);
        auto* topRow = new QHBoxLayout();
        topRow->addWidget(new QLabel(QStringLiteral("Key %1 : Numpad").arg(QString::fromStdString(keyId)), card));
        auto* assign = new QPushButton(QStringLiteral("Assign Key"), card);
        auto* minimize = new QPushButton(QStringLiteral("Minimize"), card);
        topRow->addStretch();
        topRow->addWidget(assign);
        topRow->addWidget(minimize);
        cardLayout->addLayout(topRow);
        auto* bottomRow = new QHBoxLayout();
        auto* toggle = new QCheckBox(QStringLiteral("Toggle"), card);
        auto* repeat = new QCheckBox(QStringLiteral("Repeat while held"), card);
        repeat->setChecked(config.repeatWhileHeld);
        auto* gesture = new QComboBox(card);
        gesture->addItem(QStringLiteral("Gesture"));
        gesture->setMinimumWidth(130);
        auto* action = new QComboBox(card);
        action->addItem(QString::fromStdString(config.actions.empty() ? "Action" : config.actions.begin()->second.id));
        action->setMinimumWidth(170);
        auto* edit = new QPushButton(QStringLiteral("Edit"), card);
        auto* remove = new QPushButton(QStringLiteral("Delete"), card);
        bottomRow->addWidget(toggle);
        bottomRow->addWidget(repeat);
        bottomRow->addStretch();
        bottomRow->addWidget(gesture);
        bottomRow->addWidget(action);
        bottomRow->addWidget(edit);
        bottomRow->addWidget(remove);
        cardLayout->addLayout(bottomRow);
        connect(assign, &QPushButton::clicked, this, [this, keyId]() { editKey(QString::fromStdString(keyId)); });
        connect(edit, &QPushButton::clicked, this, [this, keyId]() { editKey(QString::fromStdString(keyId)); });
        connect(remove, &QPushButton::clicked, this, [this, keyId]() {
            auto* currentPage = profiles_.currentPage();
            if (!currentPage) return;
            currentPage->keys.erase(keyId);
            gestures_.removeKey(keyId);
            saveCurrentProfile();
            clearEditor();
            rebuildGrid();
        });
        connect(minimize, &QPushButton::clicked, card, &QWidget::hide);
        keyGrid_->addWidget(card, index, 0);
        ++index;
    }
}

void MainWindow::handleKeyEvent(core::KeyEvent event) {
    if (waitingForKey_ && event.pressed) {
        waitingForKey_ = false;
        keyIdEdit_->setText(QString::fromStdString(event.keyId));
        statusLabel_->setText(QStringLiteral("ENABLED"));
        return;
    }
    gestures_.handleEvent(event);
    gestures_.flush(event.timestamp);
}

void MainWindow::updateEnabled(bool enabled) {
    gestures_.setEnabled(enabled);
    statusLabel_->setText(enabled ? QStringLiteral("ENABLED") : QStringLiteral("DISABLED"));
}

void MainWindow::showProfile(int row) {
    if (row >= 0 && row < static_cast<int>(profiles_.profiles().size())) {
        profiles_.select(profiles_.profiles()[static_cast<std::size_t>(row)].name);
        clearEditor();
        editor_->setVisible(false);
        rebuildGrid();
    }
}

void MainWindow::clearEditor() {
    editingKeyId_.clear();
    keyIdEdit_->clear();
    nameEdit_->clear();
    iconEdit_->clear();
    valueEdit_->clear();
    actionCombo_->setCurrentIndex(0);
    gestureCombo_->setCurrentIndex(0);
    toggleEdit_->setChecked(false);
    repeatEdit_->setChecked(true);
    deleteButton_->setEnabled(false);
}

void MainWindow::editKey(const QString& keyId) {
    const auto* page = profiles_.currentPage();
    if (!page || !page->keys.contains(keyId.toStdString())) return;
    const auto& key = page->keys.at(keyId.toStdString());
    editor_->setVisible(true);
    editingKeyId_ = keyId;
    keyIdEdit_->setText(keyId);
    nameEdit_->setText(QString::fromStdString(key.name));
    iconEdit_->setText(QString::fromStdString(key.icon));
    valueEdit_->clear();
    toggleEdit_->setChecked(key.toggle);
    repeatEdit_->setChecked(key.repeatWhileHeld);
    deleteButton_->setEnabled(true);
    if (!key.actions.empty()) {
        const auto& action = key.actions.begin()->second;
        valueEdit_->setText(QString::fromStdString(action.value));
        const auto index = actionCombo_->findData(QString::fromStdString(action.id));
        actionCombo_->setCurrentIndex(index < 0 ? 0 : index);
        gestureCombo_->setCurrentIndex(static_cast<int>(key.actions.begin()->first));
    }
}

void MainWindow::chooseEmptyKey() {
    clearEditor();
    editor_->setVisible(true);
    waitingForKey_ = true;
    statusLabel_->setText(QStringLiteral("PRESS A KEY"));
}

void MainWindow::cancelEdit() {
    waitingForKey_ = false;
    clearEditor();
    editor_->setVisible(false);
    statusLabel_->setText(enabledBox_->isChecked() ? QStringLiteral("ENABLED") : QStringLiteral("DISABLED"));
}

void MainWindow::changePage(int index) {
    if (profiles_.selectPage(static_cast<std::size_t>(index))) {
        clearEditor();
        rebuildGrid();
    }
}

void MainWindow::nextPage() {
    if (profiles_.nextPage()) {
        clearEditor();
        rebuildGrid();
    }
}

void MainWindow::previousPage() {
    if (profiles_.previousPage()) {
        clearEditor();
        rebuildGrid();
    }
}

void MainWindow::saveKey() {
    const auto keyId = keyIdEdit_->text().trimmed().toStdString();
    if (keyId.empty()) return;
    auto* page = profiles_.currentPage();
    if (!page) return;
    if (!editingKeyId_.isEmpty() && editingKeyId_.toStdString() != keyId) {
        page->keys.erase(editingKeyId_.toStdString());
    }
    core::KeyConfig key;
    key.keyId = keyId;
    key.name = nameEdit_->text().trimmed().toStdString();
    key.icon = iconEdit_->text().trimmed().toStdString();
    key.toggle = toggleEdit_->isChecked();
    key.repeatWhileHeld = repeatEdit_->isChecked();
    const auto actionId = actionCombo_->currentData().toString().toStdString();
    if (actionId != "none") {
        const auto actionType = actionId == "show_desktop" || actionId == "task_manager" || actionId == "lock_pc"
            ? core::ActionType::System
            : (actionId == "alt_tab" || actionId == "win_tab" || actionId == "close_window"
                ? core::ActionType::Keyboard
                : (actionId == "left_click" || actionId == "right_click" || actionId == "middle_click" ||
                   actionId == "scroll_up" || actionId == "scroll_down" ? core::ActionType::Mouse :
                                     (actionId == "open_application" || actionId == "open_file" || actionId == "open_folder" ? core::ActionType::Application :
                                        (actionId == "open_website" || actionId == "screenshot" ? core::ActionType::System :
                                         (actionId == "keyboard_shortcut" || actionId == "type_text" ? core::ActionType::Keyboard : core::ActionType::Media)))));
        key.actions[static_cast<core::GestureType>(gestureCombo_->currentData().toInt())] =
            {actionType, actionId, valueEdit_->text().trimmed().toStdString()};
    }
    page->keys[keyId] = key;
    editingKeyId_ = QString::fromStdString(keyId);
    gestures_.registerKey(key);
    saveCurrentProfile();
    rebuildGrid();
    editKey(editingKeyId_);
}

void MainWindow::deleteKey() {
    auto* page = profiles_.currentPage();
    if (!page || editingKeyId_.isEmpty()) return;
    page->keys.erase(editingKeyId_.toStdString());
    gestures_.removeKey(editingKeyId_.toStdString());
    saveCurrentProfile();
    clearEditor();
    editor_->setVisible(false);
    rebuildGrid();
}

void MainWindow::addProfile() {
    const auto name = QStringLiteral("Profile %1").arg(profileList_->count() + 1);
    if (profiles_.add({name.toStdString(), {{"Main", {}}}})) {
        profileList_->addItem(name);
        profileList_->setCurrentRow(profileList_->count() - 1);
        saveCurrentProfile();
    }
}

void MainWindow::deleteProfile() {
    const auto row = profileList_->currentRow();
    if (row < 0 || row >= static_cast<int>(profiles_.profiles().size())) return;
    const auto name = profiles_.profiles()[static_cast<std::size_t>(row)].name;
    if (name == "Default") {
        QMessageBox::information(this, QStringLiteral("Profile"), QStringLiteral("Default cannot be deleted."));
        return;
    }
    profiles_.remove(name);
    profileList_->clear();
    for (const auto& profile : profiles_.profiles()) profileList_->addItem(QString::fromStdString(profile.name));
    profileList_->setCurrentRow(0);
    rebuildGrid();
}

void MainWindow::openSettings() {
    if (contentStack_) contentStack_->setCurrentIndex(1);
}

void MainWindow::restoreFromTray() {
    showNormal();
    raise();
    activateWindow();
}

void MainWindow::closeEvent(QCloseEvent* event) {
    if (tray_ && tray_->isVisible()) {
        hide();
        event->ignore();
        return;
    }
    rawInput_.stop();
    event->accept();
}

QString MainWindow::profilePath() const {
    const auto directory = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation) + QStringLiteral("/profiles");
    QDir().mkpath(directory);
    return directory + QStringLiteral("/Default.json");
}

void MainWindow::saveCurrentProfile() {
    const auto* profile = profiles_.current();
    if (!profile) return;
    std::string error;
    storage_.saveProfile(*profile, profilePath().toStdString(), error);
}
} // namespace numpad_streamdeck::ui