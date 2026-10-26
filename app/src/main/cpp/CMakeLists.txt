cmake_minimum_required(VERSION 3.22.1)

project(agent_simulation_native LANGUAGES CXX)

add_library(
    agent_simulation_native
    SHARED
    native-lib.cpp
)

target_compile_features(
    agent_simulation_native
    PRIVATE
    cxx_std_17
)

target_compile_options(
    agent_simulation_native
    PRIVATE
    -Wall
    -Wextra
)

find_library(
    android_log
    log
)

target_link_libraries(
    agent_simulation_native
    PRIVATE
    ${android_log}
)
