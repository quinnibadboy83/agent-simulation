
package com.agentsimulation.engine

/**
 * Kotlin interface to the native llama.cpp inference engine.
 *
 * Native operations are blocking. Call model loading and generation
 * from a background thread, not the Android main thread.
 */
class NativeInferenceBridge : AutoCloseable {

    companion object {
        init {
            System.loadLibrary("agent_simulation_native")
        }
    }

    private external fun nativeGetEngineStatus(): String

    private external fun nativeLoadModel(modelPath: String): String

    private external fun nativeGenerate(prompt: String): String

    private external fun nativeClose()

    fun getEngineStatus(): String {
        return try {
            nativeGetEngineStatus()
        } catch (error: UnsatisfiedLinkError) {
            "Native library unavailable: ${error.message}"
        }
    }

    fun loadModel(modelPath: String): String {
        require(modelPath.isNotBlank()) {
            "Model path cannot be empty."
        }

        return nativeLoadModel(modelPath)
    }

    fun generate(prompt: String): String {
        require(prompt.isNotBlank()) {
            "Prompt cannot be empty."
        }

        return nativeGenerate(prompt)
    }

    override fun close() {
        nativeClose()
    }
}
