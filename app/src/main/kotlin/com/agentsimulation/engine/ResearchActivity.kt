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
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Separate Researcher screen.
 * MainActivity and the native local inference engine remain untouched.
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
                savedInstanceState?.getString(STATE_QUERY).orEmpty()
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
                "Ready. Sources: Wikipedia, arXiv and GitHub where relevant."
            setTextIsSelectable(true)
        }

        resultText = TextView(this).apply {
            textSize = 14f
            text = savedInstanceState?.getString(STATE_RESULT)
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

        super.onSaveInstanceState(outState)
    }

    private fun runResearch() {
        val query = queryInput.text.toString().trim()

        if (query.isEmpty()) {
            statusText.text = "Enter a research question first."
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

        resultText.text = "Research in progress..."

        executor.execute {
            try {
                val report = researchService.search(query)

                mainHandler.post {
                    if (screenDestroyed) {
                        return@post
                    }

                    latestReport = report
                    resultText.text = report.toDisplayText()

                    statusText.text =
                        "Research complete. ${report.sources.size} source(s) collected. Review the limitations in the report."

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
        private const val STATE_QUERY = "research_query"
        private const val STATE_RESULT = "research_result"
        private const val STATE_STATUS = "research_status"
    }
}
