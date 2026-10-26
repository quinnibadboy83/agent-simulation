
cmake_minimum_required(VERSION 3.22.1)

project(agent_simulation_native LANGUAGES C CXX)

include(FetchContent)

# Build a portable Android CPU version.
set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
set(GGML_OPENMP OFF CACHE BOOL "" FORCE)
set(GGML_LLAMAFILE OFF CACHE BOOL "" FORCE)
set(LLAMA_OPENSSL OFF CACHE BOOL "" FORCE)

# Keep the Android build focused on the inference library.
set(LLAMA_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_SERVER OFF CACHE BOOL "" FORCE)
set(LLAMA_CURL OFF CACHE BOOL "" FORCE)

FetchContent_Declare(
    llama_cpp
    GIT_REPOSITORY https://github.com/ggml-org/llama.cpp.git
    GIT_TAG b11897
    GIT_SHALLOW TRUE
    GIT_SUBMODULES_RECURSE TRUE
)

FetchContent_MakeAvailable(llama_cpp)

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

find_library(android_log log)

target_link_libraries(
    agent_simulation_native
    PRIVATE
    llama
    ${android_log}
)
