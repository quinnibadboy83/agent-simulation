
package com.agentsimulation.engine

import android.content.Context
import android.net.Uri
import java.io.BufferedInputStream
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.security.MessageDigest

/**
 * Imports GGUF models into app-private storage.
 *
 * Uses a stable filename for each source URI so selecting the
 * same model again does not create another full model copy.
 */
object LocalModelFileManager {

    private const val GGUF_MAGIC = "GGUF"
    private const val MODEL_DIRECTORY = "models"

    @Throws(IOException::class)
    fun importModel(context: Context, sourceUri: Uri): File {
        val modelDirectory = File(context.filesDir, MODEL_DIRECTORY)

        if (!modelDirectory.exists() && !modelDirectory.mkdirs()) {
            throw IOException("Could not create the private model directory.")
        }

        val modelHash = sha256(sourceUri.toString())

        val destination = File(
            modelDirectory,
            "model-$modelHash.gguf"
        )

        // Reuse an existing complete GGUF copy.
        if (isValidGguf(destination)) {
            return destination
        }

        // Remove an incomplete copy before importing again.
        if (destination.exists() && !destination.delete()) {
            throw IOException("Could not replace an incomplete model copy.")
        }

        val inputStream = context.contentResolver.openInputStream(sourceUri)
            ?: throw IOException("Could not open the selected model file.")

        try {
            BufferedInputStream(inputStream).use { input ->
                val magic = ByteArray(4)
                val bytesRead = input.read(magic)

                if (
                    bytesRead != 4 ||
                    String(magic, Charsets.US_ASCII) != GGUF_MAGIC
                ) {
                    throw IOException(
                        "The selected file is not a valid GGUF file."
                    )
                }

                FileOutputStream(destination).buffered().use { output ->
                    output.write(magic)
                    input.copyTo(output)
                    output.flush()
                }
            }
        } catch (error: Exception) {
            destination.delete()

            if (error is IOException) {
                throw error
            }

            throw IOException(
                "Could not copy the selected model file.",
                error
            )
        }

        if (!isValidGguf(destination)) {
            destination.delete()

            throw IOException(
                "The selected model file appears empty or incomplete."
            )
        }

        return destination
    }

    /**
     * Checks the GGUF file signature and basic file size.
     */
    private fun isValidGguf(file: File): Boolean {
        if (!file.isFile || file.length() <= 4L) {
            return false
        }

        return try {
            BufferedInputStream(file.inputStream()).use { input ->
                val magic = ByteArray(4)

                if (input.read(magic) != 4) {
                    return false
                }

                String(magic, Charsets.US_ASCII) == GGUF_MAGIC
            }
        } catch (_: Exception) {
            false
        }
    }

    /**
     * Creates a stable SHA-256 identifier from the source URI.
     */
    private fun sha256(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(value.toByteArray(Charsets.UTF_8))

        return digest.joinToString("") { byte ->
            "%02x".format(byte)
        }
    }
}
