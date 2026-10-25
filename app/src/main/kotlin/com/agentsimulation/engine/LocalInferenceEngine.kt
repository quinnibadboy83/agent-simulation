
package com.agentsimulation.engine

import java.io.File

/**
 * Contract between the Android app and its local model-inference backend.
 * The implementation will run inference on-device.
 */
interface LocalInferenceEngine : AutoCloseable {

    /**
     * Loads a GGUF model from app-private storage.
     * Call this from a background coroutine, not the main thread.
     */
    suspend fun loadModel(modelFile: File)

    /**
     * Generates a response using the loaded local model.
     * Call this from a background coroutine, not the main thread.
     */
    suspend fun generate(prompt: String): String

    /** Releases model and native resources. */
    override fun close()
}
