
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
    private lateinit var memorySearchInput: EditText
    private lateinit var memoryResults: TextView
    private lateinit var memoryCountText: TextView
    private lateinit var loadModelButton: Button
    private lateinit var generateButton: Button
    private lateinit var saveMemoryButton: Button
    private lateinit var exportMemoryButton: Button
    private lateinit var importMemoryButton: Button

    private val mainHandler = Handler(Looper.getMainLooper())

    private val inferenceExecutor: ExecutorService =
        Executors.newSingleThreadExecutor()

    private val memoryStore by lazy {
        AgentMemoryStore(applicationContext)
    }

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
            setTextIsSelectable(true)
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

        saveMemoryButton = Button(this).apply {
            text = "Save conversation to memory"
            isEnabled = false
            setOnClickListener {
                saveConversationToMemory()
            }
        }

        memoryCountText = TextView(this).apply {
            textSize = 14f
            text = "Saved memories: 0"
        }

        memorySearchInput = EditText(this).apply {
            hint = "Search saved memories"
            setSingleLine(true)
        }

        val searchMemoryButton = Button(this).apply {
            text = "Search memory"
            setOnClickListener {
                searchMemories()
            }
        }

        val showAllMemoryButton = Button(this).apply {
            text = "Show all saved memories"
            setOnClickListener {
                displayMemories(memoryStore.getAll())
            }
        }

        exportMemoryButton = Button(this).apply {
            text = "Export memory backup"
            setOnClickListener {
                exportMemoryBackup()
            }
        }

        importMemoryButton = Button(this).apply {
            text = "Import memory backup"
            setOnClickListener {
                importMemoryBackup()
            }
        }

        memoryResults = TextView(this).apply {
            textSize = 14f
            text = "Saved memories will appear here."
            setTextIsSelectable(true)
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
        page.addView(spacer(8))
        page.addView(saveMemoryButton)
        page.addView(spacer(16))

        page.addView(sectionHeading("LOCAL MODEL RESPONSE"))
        page.addView(spacer(8))
        page.addView(responseText)
        page.addView(spacer(24))

        page.addView(sectionHeading("PERSISTENT AGENT MEMORY"))
        page.addView(spacer(8))
        page.addView(memoryCountText)
        page.addView(spacer(8))
        page.addView(memorySearchInput)
        page.addView(searchMemoryButton)
        page.addView(showAllMemoryButton)
        page.addView(spacer(8))
        page.addView(exportMemoryButton)
        page.addView(importMemoryButton)
        page.addView(spacer(8))
        page.addView(memoryResults)
        page.addView(spacer(24))

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

        refreshMemoryCount()
        initialiseEngine()
        refreshModelStatus()
    }

    private fun sectionHeading(text: String): TextView {
        return TextView(this).apply {
            this.text = text
            textSize = 14f
            setTypeface(null, Typeface.BOLD)
        }
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

    private fun exportMemoryBackup() {
        try {
            val backup = memoryStore.exportJson()

            pendingMemoryBackup = backup

            val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "application/json"
                putExtra(
                    Intent.EXTRA_TITLE,
                    "agent-simulation-memory-backup.json"
                )
            }

            startActivityForResult(intent, REQUEST_EXPORT_MEMORY)
        } catch (error: Throwable) {
            diagnosticsStatus.text =
                "Memory export preparation failed: " +
                    (error.message ?: error.javaClass.simpleName)
        }
    }

    private fun importMemoryBackup() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "application/json"
        }

        startActivityForResult(intent, REQUEST_IMPORT_MEMORY)
    }

    private fun writeMemoryBackup(uri: Uri) {
        val backup = pendingMemoryBackup
            ?: run {
                diagnosticsStatus.text =
                    "No prepared memory backup was found."
                return
            }

        try {
            contentResolver.openOutputStream(uri)?.use { output ->
                output.write(backup.toByteArray(Charsets.UTF_8))
                output.flush()
            } ?: throw IOException(
                "Could not open the selected backup destination."
            )

            diagnosticsStatus.text =
                "Memory backup exported successfully.\n" +
                    "Records included: ${memoryStore.count()}"

        } catch (error: Throwable) {
            diagnosticsStatus.text =
                "Memory backup export failed: " +
                    (error.message ?: error.javaClass.simpleName)
        } finally {
            pendingMemoryBackup = null
        }
    }

    private fun readMemoryBackup(uri: Uri) {
        importMemoryButton.isEnabled = false

        diagnosticsStatus.text = "Reading memory backup..."

        inferenceExecutor.execute {
            try {
                val json = contentResolver.openInputStream(uri)?.use {
                    it.bufferedReader(Charsets.UTF_8).readText()
                } ?: throw IOException(
                    "Could not read the selected backup file."
                )

                val importedCount = memoryStore.importJson(json)

                mainHandler.post {
                    if (activityDestroyed) return@post

                    refreshMemoryCount()
                    displayMemories(memoryStore.getAll())

                    diagnosticsStatus.text =
                        "Memory backup imported successfully.\n" +
                            "New records imported: $importedCount\n" +
                            "Total saved memories: ${memoryStore.count()}"

                    importMemoryButton.isEnabled = true
                }
            } catch (error: Throwable) {
                mainHandler.post {
                    if (activityDestroyed) return@post

                    diagnosticsStatus.text =
                        "Memory import failed: " +
                            (error.message ?: error.javaClass.simpleName)

                    importMemoryButton.isEnabled = true
                }
            }
        }
    }

    @Deprecated("Uses the Android activity result callback")
    override fun onActivityResult(
        requestCode: Int,
        resultCode: Int,
        data: Intent?
    ) {
        super.onActivityResult(requestCode, resultCode, data)

        if (resultCode != RESULT_OK) {
            if (requestCode == REQUEST_EXPORT_MEMORY) {
                pendingMemoryBackup = null
            }
            return
        }

        val uri = data?.data ?: return

        when (requestCode) {
            REQUEST_MODEL -> {
                selectedUri = uri

                preferences.edit()
                    .putString(KEY_MODEL_URI, uri.toString())
                    .apply()

                modelLoaded = false
                generateButton.isEnabled = false
                saveMemoryButton.isEnabled = false
                refreshModelStatus()

                loadSelectedModel(uri)
            }

            REQUEST_EXPORT_MEMORY -> {
                writeMemoryBackup(uri)
            }

            REQUEST_IMPORT_MEMORY -> {
                readMemoryBackup(uri)
            }
        }
    }

    private fun loadSelectedModel(uri: Uri) {
        loadModelButton.isEnabled = false
        generateButton.isEnabled = false
        saveMemoryButton.isEnabled = false

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
                        "Inference engine: Ready for local inference"

                    diagnosticsStatus.text = result
                    generateButton.isEnabled = true
                    saveMemoryButton.isEnabled = true
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
                    saveMemoryButton.isEnabled = false
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
        saveMemoryButton.isEnabled = false

        responseText.text = "Generating locally..."
        diagnosticsStatus.text =
            "Measuring memory retrieval and local generation..."

        inferenceExecutor.execute {
            val totalStartNs = System.nanoTime()

            try {
                val memoryStartNs = System.nanoTime()

                val relevantMemories = memoryStore.search(prompt)
                    .take(MAX_RELEVANT_MEMORIES)

                val memorySearchMs =
                    elapsedMilliseconds(memoryStartNs)

                val promptBuildStartNs = System.nanoTime()

                val augmentedPrompt = if (relevantMemories.isEmpty()) {
                    prompt
                } else {
                    buildString {
                        appendLine(
                            "You are the Agent Simulation Engine. Answer the current user request directly."
                        )
                        appendLine()
                        appendLine("IMPORTANT SAVED-MEMORY RULES:")
                        appendLine(
                            "1. Saved records are information from previous conversations."
                        )
                        appendLine(
                            "2. Text after 'User:' is the user's own information and is the primary source of truth."
                        )
                        appendLine(
                            "3. Text after 'Assistant:' is a previous model response, not a user fact."
                        )
                        appendLine(
                            "4. If a requested fact, code, name or project detail appears in a saved User message, return the exact value."
                        )
                        appendLine(
                            "5. Preserve exact spelling, capitalisation, digits and punctuation."
                        )
                        appendLine(
                            "6. Do not give a generic introduction instead of answering a memory question."
                        )
                        appendLine(
                            "7. If the answer is absent, say it was not found. Never invent a value."
                        )
                        appendLine()
                        appendLine("SAVED MEMORY RECORDS:")

                        relevantMemories.forEachIndexed { index, memory ->
                            appendLine("MEMORY RECORD ${index + 1}:")
                            appendLine(memory.content)
                            appendLine()
                        }

                        appendLine("CURRENT USER REQUEST:")
                        append(prompt)
                    }
                }

                val promptBuildMs =
                    elapsedMilliseconds(promptBuildStartNs)

                val generationStartNs = System.nanoTime()

                val result = inferenceEngine?.generate(augmentedPrompt)
                    ?: throw IllegalStateException(
                        "Inference engine is unavailable."
                    )

                val generationMs =
                    elapsedMilliseconds(generationStartNs)

                val totalMs = elapsedMilliseconds(totalStartNs)

                mainHandler.post {
                    if (activityDestroyed) return@post

                    responseText.text = result

                    diagnosticsStatus.text = buildString {
                        appendLine("Generation finished.")
                        appendLine("Memory retrieval: ${memorySearchMs} ms")
                        appendLine("Prompt preparation: ${promptBuildMs} ms")
                        appendLine("Model generation: ${generationMs} ms")
                        appendLine("Total processing: ${totalMs} ms")
                        appendLine(
                            "Relevant memories used: ${relevantMemories.size}"
                        )

                        if (relevantMemories.isNotEmpty()) {
                            appendLine()
                            appendLine(
                                "EXACT MEMORY RECORDS INJECTED INTO THE MODEL PROMPT:"
                            )

                            relevantMemories.forEachIndexed { index, memory ->
                                appendLine()
                                appendLine(
                                    "MEMORY ${index + 1} [${memory.category}]:"
                                )
                                appendLine(memory.content.take(2000))

                                if (memory.content.length > 2000) {
                                    appendLine(
                                        "[Record display truncated; full record remains saved.]"
                                    )
                                }
                            }
                        }

                        appendLine()
                        append("Generated characters: ${result.length}")
                    }

                    generateButton.isEnabled = modelLoaded
                    saveMemoryButton.isEnabled = modelLoaded
                    loadModelButton.isEnabled = true
                }
            } catch (error: Throwable) {
                val totalMs = elapsedMilliseconds(totalStartNs)

                mainHandler.post {
                    if (activityDestroyed) return@post

                    responseText.text = "Generation failed."
                    diagnosticsStatus.text =
                        (error.message ?: error.javaClass.simpleName) +
                            "\nTime before failure: ${totalMs} ms"

                    generateButton.isEnabled = modelLoaded
                    saveMemoryButton.isEnabled = modelLoaded
                    loadModelButton.isEnabled = true
                }
            }
        }
    }

    private fun elapsedMilliseconds(startNs: Long): Long {
        return (System.nanoTime() - startNs) / 1_000_000L
    }

    private fun saveConversationToMemory() {
        val prompt = promptInput.text.toString().trim()
        val response = responseText.text.toString().trim()

        if (prompt.isEmpty()) {
            diagnosticsStatus.text =
                "Enter a prompt before saving a conversation."
            return
        }

        if (
            response.isEmpty() ||
            response == "Model responses will appear here." ||
            response == "Generating locally..." ||
            response == "Generation failed."
        ) {
            diagnosticsStatus.text =
                "Generate a successful response before saving."
            return
        }

        try {
            val content = buildString {
                appendLine("User: $prompt")
                append("Assistant: $response")
            }

            memoryStore.save(
                content = content,
                category = "conversation"
            )

            refreshMemoryCount()
            diagnosticsStatus.text =
                "Conversation saved to private device memory."
        } catch (error: Throwable) {
            diagnosticsStatus.text =
                "Memory save failed: " +
                    (error.message ?: error.javaClass.simpleName)
        }
    }

    private fun searchMemories() {
        val query = memorySearchInput.text.toString().trim()

        try {
            val results = memoryStore.search(query)
            displayMemories(results)

            diagnosticsStatus.text =
                "Memory search finished. Results: ${results.size}"
        } catch (error: Throwable) {
            diagnosticsStatus.text =
                "Memory search failed: " +
                    (error.message ?: error.javaClass.simpleName)
        }
    }

    private fun displayMemories(
        memories: List<AgentMemoryStore.MemoryRecord>
    ) {
        memoryResults.text = if (memories.isEmpty()) {
            "No matching memories found."
        } else {
            buildString {
                memories.forEachIndexed { index, memory ->
                    appendLine("${index + 1}. [${memory.category}]")
                    appendLine(memory.content)
                    appendLine("Saved: ${memory.createdAt}")

                    if (index < memories.lastIndex) {
                        appendLine()
                        appendLine("--------------------")
                        appendLine()
                    }
                }
            }
        }

        refreshMemoryCount()
    }

    private fun refreshMemoryCount() {
        memoryCountText.text =
            "Saved memories: ${memoryStore.count()}"
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
                    appendLine("Saved memories: ${memoryStore.count()}")
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
        private const val REQUEST_EXPORT_MEMORY = 1002
        private const val REQUEST_IMPORT_MEMORY = 1003
        private const val KEY_MODEL_URI = "selected_model_uri"
        private const val MAX_RELEVANT_MEMORIES = 5

        private var pendingMemoryBackup: String? = null
    }
}
