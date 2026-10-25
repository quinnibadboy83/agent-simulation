
package com.agentsimulation.engine

import android.content.Context
import android.net.Uri
import java.io.BufferedInputStream
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.util.UUID

/**
 * Imports a selected GGUF model into app-private storage.
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

        val destination = File(
            modelDirectory,
            "model-${UUID.randomUUID()}.gguf"
        )

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
                }
            }
        } catch (error: Exception) {
            destination.delete()

            if (error is IOException) throw error

            throw IOException(
                "Could not copy the selected model file.",
                error
            )
        }

        if (!destination.isFile || destination.length() <= 4) {
            destination.delete()
            throw IOException(
                "The selected model file appears empty or incomplete."
            )
        }

        return destination
    }
}
