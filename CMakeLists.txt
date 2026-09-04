cmake_minimum_required(VERSION 3.20)

project(NumpadStreamDeck VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(CTest)

find_package(Qt6 COMPONENTS Core Widgets QUIET)

add_library(numpad_streamdeck_core
    src/numpad_streamdeck/core/gesture_detector.cpp
    src/numpad_streamdeck/profiles/profile.cpp
    src/numpad_streamdeck/actions/action_manager.cpp
    src/numpad_streamdeck/actions/builtin_actions.cpp
)

target_include_directories(numpad_streamdeck_core PUBLIC
    src
)

if(BUILD_TESTING)
    add_executable(numpad_streamdeck_core_tests
        tests/core_tests.cpp
    )
    target_link_libraries(numpad_streamdeck_core_tests PRIVATE numpad_streamdeck_core)
    add_test(NAME numpad_streamdeck_core_tests COMMAND numpad_streamdeck_core_tests)
endif()

if(Qt6_FOUND)
    set(CMAKE_AUTOMOC ON)
    find_program(WINDEPLOYQT_EXECUTABLE
        NAMES windeployqt6.exe windeployqt.exe
        HINTS "${CMAKE_PREFIX_PATH}/bin" "${Qt6_DIR}/../../../bin"
    )
    target_sources(numpad_streamdeck_core PRIVATE
        src/numpad_streamdeck/storage/json_storage.cpp
    )
    target_link_libraries(numpad_streamdeck_core PUBLIC Qt6::Core)
    add_executable(NumpadStreamDeck
        src/numpad_streamdeck/main.cpp
        src/numpad_streamdeck/input/raw_input.cpp
        src/numpad_streamdeck/ui/main_window.cpp
    )
    target_link_libraries(NumpadStreamDeck PRIVATE numpad_streamdeck_core Qt6::Core Qt6::Widgets)
    add_custom_command(TARGET NumpadStreamDeck POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${CMAKE_SOURCE_DIR}/resources" "$<TARGET_FILE_DIR:NumpadStreamDeck>/resources"
        COMMAND ${CMAKE_COMMAND} -E copy_directory
            "${CMAKE_SOURCE_DIR}/config" "$<TARGET_FILE_DIR:NumpadStreamDeck>/config"
        COMMENT "Copying Numpad Stream Deck resources"
    )
    if(WINDEPLOYQT_EXECUTABLE)
        add_custom_command(TARGET NumpadStreamDeck POST_BUILD
            COMMAND "${WINDEPLOYQT_EXECUTABLE}"
                "$<IF:$<CONFIG:Debug>,--debug,--release>"
                --no-translations
                "$<TARGET_FILE:NumpadStreamDeck>"
            COMMENT "Deploying Qt runtime next to NumpadStreamDeck.exe"
        )
    endif()
endif()