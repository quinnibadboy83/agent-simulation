package com.agentsimulation.engine

/**
 * Connects the Android application to its native C++ library.
 *
 * This is the native bridge only. Actual AI inference will be
 * integrated separately using llama.cpp.
 */
class NativeInferenceBridge {

    companion object {
        init {
            System.loadLibrary("agent_simulation_native")
        }
    }

    /**
     * Returns the current native engine status.
     */
    external fun nativeGetEngineStatus(): String

    /**
     * Provides a safe entry point for checking native library status.
     */
    fun getEngineStatus(): String {
        return try {
            nativeGetEngineStatus()
        } catch (error: UnsatisfiedLinkError) {
            "Native library unavailable: ${error.message}"
        }
    }
}
