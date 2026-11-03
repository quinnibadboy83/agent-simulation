package com.agentsimulation.engine

import android.app.Activity
import android.graphics.Typeface
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
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Separate Researcher screen.
 *
 * The existing MainActivity and native local inference engine
 * remain untouched.
 */
class ResearchActivity : Activity() {

    private lateinit var queryInput: EditText
    private lateinit var resultText: TextView
    private lateinit var searchButton: Button
    private lateinit var saveButton: Button
    private lateinit var statusText: TextView

    private val mainHandler = Handler(Looper.getMainLooper())

    private val executor: ExecutorService =
        Executors.newSingleThreadExecutor()

    private val researchService by lazy {
        FreeResearchService()
    }

    private val memoryStore by lazy {
        AgentMemoryStore(applicationContext)
    }

    @Volatile
    private var screenDestroyed = false

    private var latestReport: FreeResearchReport? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        screenDestroyed = false

        val padding = (
            20 * resources.displayMetrics.density
        ).toInt()

        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
            gravity = Gravity.TOP
        }

        val title = TextView(this).apply {
            text = "Free Researcher"
            textSize = 26f
            setTypeface(null, Typeface.BOLD)
        }

        val explanation = TextView(this).apply {
            text =
                "Search public sources without a paid search API key. Results are evidence to review, not verified conclusions."
            textSize = 15f
        }

        queryInput = EditText(this).apply {
            hint = "Enter a research question (maximum 400 characters)"
            minLines = 3
            maxLines = 5
            gravity = Gravity.TOP

            setText(
                savedInstanceState
                    ?.getString(STATE_QUERY)
                    .orEmpty()
            )
        }

        searchButton = Button(this).apply {
            text = "Search public sources"

            setOnClickListener {
                runResearch()
            }
        }

        saveButton = Button(this).apply {
            text = "Save research to persistent memory"
            isEnabled = false

            setOnClickListener {
                saveLatestReport()
            }
        }

        statusText = TextView(this).apply {
            textSize = 14f
            text =
                "Ready. Sources: general web, Wikipedia, arXiv and GitHub where relevant."
            setTextIsSelectable(true)
        }

        resultText = TextView(this).apply {
            textSize = 14f
            text = savedInstanceState
                ?.getString(STATE_RESULT)
                ?: "Your research results will appear here."

            setTextIsSelectable(true)
        }

        page.addView(title)
        page.addView(spacer(8))
        page.addView(explanation)
        page.addView(spacer(16))
        page.addView(queryInput)
        page.addView(searchButton)
        page.addView(saveButton)
        page.addView(spacer(12))
        page.addView(statusText)
        page.addView(spacer(12))
        page.addView(resultText)

        val scroll = ScrollView(this).apply {
            addView(
                page,
                ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
            )
        }

        setContentView(scroll)

        if (savedInstanceState != null) {
            statusText.text = savedInstanceState.getString(
                STATE_STATUS,
                "Ready."
            )

            latestReport = savedInstanceState
                .getString(STATE_REPORT_JSON)
                ?.let { decodeReport(it) }

            saveButton.isEnabled = latestReport != null

            val wasSearching = savedInstanceState.getBoolean(
                STATE_SEARCHING,
                false
            )

            if (wasSearching) {
                statusText.text =
                    "The previous search was interrupted by screen recreation. Start the search again."
                searchButton.isEnabled = true
            }
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        if (::queryInput.isInitialized) {
            outState.putString(
                STATE_QUERY,
                queryInput.text.toString()
            )
        }

        if (::resultText.isInitialized) {
            outState.putString(
                STATE_RESULT,
                resultText.text.toString()
            )
        }

        if (::statusText.isInitialized) {
            outState.putString(
                STATE_STATUS,
                statusText.text.toString()
            )
        }

        outState.putBoolean(
            STATE_SEARCHING,
            ::searchButton.isInitialized &&
                !searchButton.isEnabled
        )

        latestReport?.let { report ->
            outState.putString(
                STATE_REPORT_JSON,
                encodeReport(report)
            )
        }

        super.onSaveInstanceState(outState)
    }

    // ---------------------------------------------------------
    // RESEARCH
    // ---------------------------------------------------------

    private fun runResearch() {
        val query = queryInput.text.toString().trim()

        if (query.isEmpty()) {
            statusText.text =
                "Enter a research question first."
            return
        }

        if (query.length > 400) {
            statusText.text =
                "Keep the question to 400 characters or fewer."
            return
        }

        searchButton.isEnabled = false
        saveButton.isEnabled = false
        latestReport = null

        statusText.text =
            "Searching public sources. This can take several seconds."

        resultText.text =
            "Research in progress..."

        executor.execute {
            try {
                val report = researchService.search(query)

                mainHandler.post {
                    if (screenDestroyed) {
                        return@post
                    }

                    latestReport = report

                    resultText.text =
                        report.toDisplayText()

                    statusText.text =
                        "Research complete. ${report.sources.size} source(s) collected. Review the source assessments and limitations."

                    saveButton.isEnabled = true
                    searchButton.isEnabled = true
                }
            } catch (error: Exception) {
                val message =
                    error.message ?: error.javaClass.simpleName

                mainHandler.post {
                    if (screenDestroyed) {
                        return@post
                    }

                    resultText.text =
                        "RESEARCH FAILED\n\n$message\n\nNo results have been invented or saved."

                    statusText.text =
                        "Search failed. Check the reported error and try again."

                    searchButton.isEnabled = true
                    saveButton.isEnabled = false
                }
            }
        }
    }

    // ---------------------------------------------------------
    // PERSISTENT MEMORY
    // ---------------------------------------------------------

    private fun saveLatestReport() {
        val report = latestReport

        if (report == null) {
            statusText.text =
                "There is no completed research report to save."
            return
        }

        try {
            val record = memoryStore.save(
                content = report.toMemoryContent(),
                category = "research"
            )

            statusText.text =
                "Saved research to persistent device memory. Memory record: ${record.id}"
        } catch (error: Exception) {
            statusText.text =
                "Could not save research: ${error.message ?: error.javaClass.simpleName}"
        }
    }

    // ---------------------------------------------------------
    // REPORT ROTATION STATE
    // ---------------------------------------------------------

    private fun encodeReport(
        report: FreeResearchReport
    ): String {
        val sourceArray = JSONArray()

        report.sources.forEach { source ->
            sourceArray.put(
                JSONObject().apply {
                    put("provider", source.provider)
                    put("title", source.title)
                    put("url", source.url)
                    put("summary", source.summary)
                }
            )
        }

        val notesArray = JSONArray()

        report.providerNotes.forEach {
            notesArray.put(it)
        }

        return JSONObject().apply {
            put("query", report.query)
            put("sources", sourceArray)
            put("providerNotes", notesArray)
        }.toString()
    }

    private fun decodeReport(
        json: String
    ): FreeResearchReport? {
        return try {
            val root = JSONObject(json)

            val query = root.optString("query")
            val sourceArray = root.optJSONArray("sources")
                ?: return null

            val notesArray = root.optJSONArray("providerNotes")
                ?: JSONArray()

            val sources = mutableListOf<FreeResearchSource>()

            for (index in 0 until sourceArray.length()) {
                val item = sourceArray.optJSONObject(index)
                    ?: continue

                val url = item.optString("url")

                if (
                    !url.startsWith("https://") &&
                    !url.startsWith("http://")
                ) {
                    continue
                }

                sources.add(
                    FreeResearchSource(
                        provider = item.optString("provider"),
                        title = item.optString("title"),
                        url = url,
                        summary = item.optString("summary")
                    )
                )
            }

            val notes = mutableListOf<String>()

            for (index in 0 until notesArray.length()) {
                val note = notesArray.optString(index)

                if (note.isNotBlank()) {
                    notes.add(note)
                }
            }

            if (query.isBlank()) {
                return null
            }

            FreeResearchReport(
                query = query,
                sources = sources,
                providerNotes = notes
            )
        } catch (_: Exception) {
            null
        }
    }

    // ---------------------------------------------------------
    // UI HELPERS
    // ---------------------------------------------------------

    private fun spacer(heightDp: Int): TextView {
        return TextView(this).apply {
            height = (
                heightDp * resources.displayMetrics.density
            ).toInt()
        }
    }

    override fun onDestroy() {
        screenDestroyed = true
        executor.shutdownNow()
        super.onDestroy()
    }

    companion object {
        private const val STATE_QUERY =
            "research_query"

        private const val STATE_RESULT =
            "research_result"

        private const val STATE_STATUS =
            "research_status"

        private const val STATE_REPORT_JSON =
            "research_report_json"

        private const val STATE_SEARCHING =
            "research_searching"
    }
}
