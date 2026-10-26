package com.agentsimulation.engine

import android.app.Activity
import android.content.Intent
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.io.File
import java.io.IOException
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : Activity() {

    private lateinit var modelStatus: TextView
    private lateinit var runtimeStatus: TextView
    private lateinit var diagnosticsStatus: TextView
    private lateinit var responseText: TextView
    private lateinit var promptInput: EditText
    private lateinit var loadModelButton: Button
    private lateinit var generateButton: Button

    private val mainHandler = Handler(Looper.getMainLooper())

    private val inferenceExecutor: ExecutorService =
        Executors.newSingleThreadExecutor()

    private var inferenceEngine: NativeInferenceBridge? = null
    private var selectedUri: Uri? = null
    private var importedModel: File? = null
    private var modelLoaded = false
    private var activityDestroyed = false

    private val preferences by lazy {
        getSharedPreferences("engine_settings", MODE_PRIVATE)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        selectedUri = preferences.getString(
            KEY_MODEL_URI,
            null
        )?.let(Uri::parse)

        val padding = (20 * resources.displayMetrics.density).toInt()

        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
            gravity = Gravity.TOP
        }

        val title = TextView(this).apply {
            text = "Agent Simulation Engine"
            textSize = 26f
            setTypeface(null, Typeface.BOLD)
        }

        val subtitle = TextView(this).apply {
            text = "Your portable, local-first AI agent platform"
            textSize = 15f
        }

        modelStatus = TextView(this).apply {
            textSize = 16f
            text = "Local model: Not loaded"
        }

        runtimeStatus = TextView(this).apply {
            textSize = 16f
            text = "Inference engine: Initialising"
        }

        diagnosticsStatus = TextView(this).apply {
            textSize = 14f
            text = "Choose a GGUF model to begin."
        }

        responseText = TextView(this).apply {
            textSize = 15f
            text = "Model responses will appear here."
            setTextIsSelectable(true)
        }

        promptInput = EditText(this).apply {
            hint = "Enter a prompt for your local model"
            minLines = 3
            maxLines = 6
            gravity = Gravity.TOP
        }

        loadModelButton = Button(this).apply {
            text = "Choose and load local GGUF model"
            setOnClickListener {
                chooseModel()
            }
        }

        generateButton = Button(this).apply {
            text = "Generate response"
            isEnabled = false
            setOnClickListener {
                generateResponse()
            }
        }

        val diagnosticsButton = Button(this).apply {
            text = "Engine diagnostics"
            setOnClickListener {
                showDiagnostics()
            }
        }

        page.addView(title)
        page.addView(spacer(8))
        page.addView(subtitle)
        page.addView(spacer(24))
        page.addView(modelStatus)
        page.addView(spacer(8))
        page.addView(runtimeStatus)
        page.addView(spacer(16))
        page.addView(loadModelButton)
        page.addView(spacer(8))
        page.addView(promptInput)
        page.addView(generateButton)
        page.addView(spacer(16))

        val responseHeading = TextView(this).apply {
            text = "LOCAL MODEL RESPONSE"
            textSize = 14f
            setTypeface(null, Typeface.BOLD)
        }

        page.addView(responseHeading)
        page.addView(spacer(8))
        page.addView(responseText)
        page.addView(spacer(16))
        page.addView(diagnosticsButton)
        page.addView(spacer(8))
        page.addView(diagnosticsStatus)

        val scrollView = ScrollView(this).apply {
            addView(
                page,
                ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
            )
        }

        setContentView(scrollView)

        initialiseEngine()
        refreshModelStatus()
    }

    private fun spacer(heightDp: Int): TextView {
        return TextView(this).apply {
            height = (
                heightDp * resources.displayMetrics.density
            ).toInt()
        }
    }

    private fun initialiseEngine() {
        runtimeStatus.text = "Inference engine: Initialising"

        inferenceExecutor.execute {
            try {
                val engine = NativeInferenceBridge()
                val status = engine.getEngineStatus()

                mainHandler.post {
                    if (activityDestroyed) {
                        engine.close()
                        return@post
                    }

                    inferenceEngine = engine
                    runtimeStatus.text = "Inference engine: Available"
                    diagnosticsStatus.text = status
                }
            } catch (error: Throwable) {
                mainHandler.post {
                    if (!activityDestroyed) {
                        runtimeStatus.text =
                            "Inference engine: Initialisation failed"

                        diagnosticsStatus.text =
                            error.message ?: error.javaClass.simpleName
                    }
                }
            }
        }
    }

    private fun chooseModel() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
        }

        startActivityForResult(intent, REQUEST_MODEL)
    }

    @Deprecated("Uses the Android activity result callback")
    override fun onActivityResult(
        requestCode: Int,
        resultCode: Int,
        data: Intent?
    ) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode != REQUEST_MODEL || resultCode != RESULT_OK) {
            return
        }

        val uri = data?.data ?: return

        selectedUri = uri

        preferences.edit()
            .putString(KEY_MODEL_URI, uri.toString())
            .apply()

        modelLoaded = false
        generateButton.isEnabled = false
        refreshModelStatus()

        loadSelectedModel(uri)
    }

    private fun loadSelectedModel(uri: Uri) {
        loadModelButton.isEnabled = false
        generateButton.isEnabled = false

        modelStatus.text = "Local model: Importing GGUF file..."
        runtimeStatus.text = "Inference engine: Loading model"
        diagnosticsStatus.text =
            "Copying the model into private app storage."

        inferenceExecutor.execute {
            var copiedFile: File? = null

            try {
                copiedFile = LocalModelFileManager.importModel(
                    applicationContext,
                    uri
                )

                val engine = inferenceEngine
                    ?: throw IllegalStateException(
                        "Native inference engine is not ready. Try again shortly."
                    )

                val result = engine.loadModel(copiedFile.absolutePath)

                if (!result.startsWith("READY:")) {
                    throw IOException(result)
                }

                mainHandler.post {
                    if (activityDestroyed) return@post

                    importedModel = copiedFile
                    modelLoaded = true

                    modelStatus.text =
                        "Local model: Loaded successfully\n" +
                        copiedFile.name

                    runtimeStatus.text =
                        "Inference engine: Ready for local CPU inference"

                    diagnosticsStatus.text = result
                    generateButton.isEnabled = true
                    loadModelButton.isEnabled = true
                }
            } catch (error: Throwable) {
                copiedFile?.delete()

                mainHandler.post {
                    if (activityDestroyed) return@post

                    modelLoaded = false
                    modelStatus.text = "Local model: Load failed"
                    runtimeStatus.text =
                        "Inference engine: Not ready"

                    diagnosticsStatus.text =
                        error.message ?: error.javaClass.simpleName

                    loadModelButton.isEnabled = true
                    generateButton.isEnabled = false
                }
            }
        }
    }

    private fun generateResponse() {
        val prompt = promptInput.text.toString().trim()

        if (prompt.isEmpty()) {
            diagnosticsStatus.text = "Enter a prompt first."
            return
        }

        if (!modelLoaded || inferenceEngine == null) {
            diagnosticsStatus.text = "Load a GGUF model first."
            return
        }

        generateButton.isEnabled = false
        loadModelButton.isEnabled = false
        responseText.text = "Generating locally..."
        diagnosticsStatus.text =
            "The model is processing your prompt on this device."

        inferenceExecutor.execute {
            try {
                val result = inferenceEngine?.generate(prompt)
                    ?: throw IllegalStateException(
                        "Inference engine is unavailable."
                    )

                mainHandler.post {
                    if (activityDestroyed) return@post

                    responseText.text = result
                    diagnosticsStatus.text =
                        "Generation finished."

                    generateButton.isEnabled = modelLoaded
                    loadModelButton.isEnabled = true
                }
            } catch (error: Throwable) {
                mainHandler.post {
                    if (activityDestroyed) return@post

                    responseText.text = "Generation failed."
                    diagnosticsStatus.text =
                        error.message ?: error.javaClass.simpleName

                    generateButton.isEnabled = modelLoaded
                    loadModelButton.isEnabled = true
                }
            }
        }
    }

    private fun showDiagnostics() {
        inferenceExecutor.execute {
            val status = try {
                inferenceEngine?.getEngineStatus()
                    ?: "Native inference engine is not initialised."
            } catch (error: Throwable) {
                error.message ?: error.javaClass.simpleName
            }

            mainHandler.post {
                if (activityDestroyed) return@post

                diagnosticsStatus.text = buildString {
                    appendLine("Application: running")
                    appendLine(
                        "Android API: ${android.os.Build.VERSION.SDK_INT}"
                    )
                    appendLine(
                        "Device: ${android.os.Build.MANUFACTURER} " +
                            android.os.Build.MODEL
                    )
                    appendLine("Model selected: ${selectedUri != null}")
                    appendLine("Model loaded: $modelLoaded")
                    appendLine("Native status: $status")
                    append(
                        "Imported model: " +
                            (importedModel?.name ?: "Not loaded")
                    )
                }
            }
        }
    }

    private fun refreshModelStatus() {
        val uri = selectedUri

        modelStatus.text = if (uri == null) {
            "Local model: Not selected"
        } else {
            "Local model: Selected\n" +
                (uri.lastPathSegment ?: "GGUF model")
        }
    }

    override fun onDestroy() {
        activityDestroyed = true

        inferenceExecutor.execute {
            try {
                inferenceEngine?.close()
            } catch (_: Throwable) {
                // Best-effort native resource cleanup.
            } finally {
                inferenceEngine = null
            }
        }

        inferenceExecutor.shutdown()
        super.onDestroy()
    }

    companion object {
        private const val REQUEST_MODEL = 1001
        private const val KEY_MODEL_URI = "selected_model_uri"
    }
}
