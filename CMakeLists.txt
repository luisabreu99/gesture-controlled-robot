cmake_minimum_required(VERSION 3.10)

project(ROBO)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)

add_executable(robo
    multiServer_02.cpp
    multiServer_01.py
    web_dashboard.py
    templates/index.html
    static/style.css
)

target_link_libraries(robo
    ${OpenCV_LIBS}
    pthread
)

include_directories(
    ${OpenCV_INCLUDE_DIRS}
)
