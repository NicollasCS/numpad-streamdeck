#include "numpad_streamdeck/ui/main_window.hpp"

#include <QApplication>

int main(int argc, char* argv[]) {
    QApplication application(argc, argv);
    numpad_streamdeck::ui::MainWindow window;
    window.show();
    return application.exec();
}