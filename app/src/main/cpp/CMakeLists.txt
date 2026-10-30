
cmake_minimum_required(VERSION 3.22.1)

project(agent_simulation_native LANGUAGES C CXX)

include(FetchContent)

# --------------------------------------------------
# ANDROID CPU BUILD CONFIGURATION
# --------------------------------------------------

set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
set(GGML_OPENMP OFF CACHE BOOL "" FORCE)
set(GGML_LLAMAFILE OFF CACHE BOOL "" FORCE)

set(LLAMA_OPENSSL OFF CACHE BOOL "" FORCE)

# Keep the Android build focused on local inference.
set(LLAMA_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_SERVER OFF CACHE BOOL "" FORCE)
set(LLAMA_CURL OFF CACHE BOOL "" FORCE)

# --------------------------------------------------
# LLAMA.CPP SOURCE
# --------------------------------------------------

FetchContent_Declare(
    llama_cpp
    GIT_REPOSITORY https://github.com/ggml-org/llama.cpp.git
    GIT_TAG b11897
    GIT_SHALLOW TRUE
    GIT_SUBMODULES_RECURSE TRUE
)

FetchContent_MakeAvailable(llama_cpp)

# --------------------------------------------------
# NATIVE INFERENCE APPLICATION
# --------------------------------------------------

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

# Optimise our JNI bridge.
target_compile_options(
    agent_simulation_native
    PRIVATE
    -O3
    -Wall
    -Wextra
)

# --------------------------------------------------
# LLAMA.CPP CPU OPTIMISATION
# --------------------------------------------------
#
# Apply Release-level optimisation to the inference
# libraries even when assembling an Android debug APK.
#
# This does not enable GPU execution or change model
# storage. It optimises native CPU compilation.

foreach(native_target llama ggml ggml-base ggml-cpu)

    if(TARGET ${native_target})

        target_compile_options(
            ${native_target}
            PRIVATE
            -O3
        )

    endif()

endforeach()

# --------------------------------------------------
# ANDROID LIBRARIES
# --------------------------------------------------

find_library(android_log log)

target_link_libraries(
    agent_simulation_native
    PRIVATE
    llama
    ${android_log}
)
