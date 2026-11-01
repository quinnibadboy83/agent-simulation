package com.agentsimulation.engine

import android.app.Activity
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.util.concurrent.Executors

class ResearchActivity : Activity() {

    private val worker = Executors.newSingleThreadExecutor()

    private val memoryStore by lazy {
        AgentMemoryStore(applicationContext)
    }

    private lateinit var questionInput: EditText
    private lateinit var resultText: TextView
    private lateinit var statusText: TextView
    private lateinit var searchButton: Button
    private lateinit var saveButton: Button

    @Volatile
    private var closed = false

    private var latestReport: FreeResearchReport? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val padding =
            (20 * resources.displayMetrics.density).toInt()

        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
            gravity = Gravity.TOP
        }

        val title = TextView(this).apply {
            text = "Agent Simulation Engine — Researcher"
            textSize = 24f
            setTypeface(null, Typeface.BOLD)
        }

        val explanation = TextView(this).apply {
            text = "Free public-source research. No search API key required."
            textSize = 14f
        }

        questionInput = EditText(this).apply {
            hint = "Enter a research question"
            minLines = 2
            maxLines = 4
            gravity = Gravity.TOP
            setText(
                savedInstanceState?.getString(STATE_QUERY).orEmpty()
            )
        }

        searchButton = Button(this).apply {
            text = "Search Wikipedia, arXiv and GitHub"
            setOnClickListener {
                runSearch()
            }
        }

        saveButton = Button(this).apply {
            text = "Save research to memory"
            isEnabled = false
            setOnClickListener {
                saveResearch()
            }
        }

        statusText = TextView(this).apply {
            text = "Ready. An internet connection is required."
            textSize = 14f
        }

        resultText = TextView(this).apply {
            text = savedInstanceState?.getString(STATE_RESULTS)
                ?: "Search results and source URLs will appear here."
            textSize = 14f
            setTextIsSelectable(true)
        }

        page.addView(title)
        page.addView(spacer(10))
        page.addView(explanation)
        page.addView(spacer(16))
        page.addView(questionInput)
        page.addView(searchButton)
        page.addView(saveButton)
        page.addView(spacer(12))
        page.addView(statusText)
        page.addView(spacer(12))
        page.addView(resultText)

        val scroll = ScrollView(this)
        scroll.addView(
            page,
            ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        )

        setContentView(scroll)
    }

    private fun runSearch() {
        val query = questionInput.text.toString().trim()

        if (query.isBlank()) {
            statusText.text = "Enter a research question first."
            return
        }

        searchButton.isEnabled = false
        saveButton.isEnabled = false

        statusText.text =
            "Searching public sources. Please wait..."

        resultText.text = "Retrieving live search results..."

        worker.execute {
            try {
                val report = FreeResearchService().search(query)

                runOnUiThread {
                    if (closed) return@runOnUiThread

                    latestReport = report
                    resultText.text = report.toDisplayText()

                    statusText.text =
                        "Search completed. Sources: ${report.sources.size}"

                    searchButton.isEnabled = true
                    saveButton.isEnabled = true
                }
            } catch (error: Throwable) {
                runOnUiThread {
                    if (closed) return@runOnUiThread

                    latestReport = null

                    resultText.text = buildString {
                        appendLine("Search failed.")
                        appendLine()
                        append(
                            error.message
                                ?: error.javaClass.simpleName
                        )
                    }

                    statusText.text =
                        "No complete research report was produced."

                    searchButton.isEnabled = true
                    saveButton.isEnabled = false
                }
            }
        }
    }

    private fun saveResearch() {
        val report = latestReport

        if (report == null) {
            statusText.text =
                "Run a successful search before saving."
            return
        }

        try {
            val record = memoryStore.save(
                content = report.toMemoryContent(),
                category = "web_research"
            )

            statusText.text =
                "Research saved to device memory. " +
                    "Record: ${record.id.take(8)}"
        } catch (error: Throwable) {
            statusText.text =
                "Memory save failed: " +
                    (error.message ?: error.javaClass.simpleName)
        }
    }

    private fun spacer(dp: Int): TextView {
        return TextView(this).apply {
            height = (
                dp * resources.displayMetrics.density
            ).toInt()
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putString(
            STATE_QUERY,
            questionInput.text.toString()
        )

        outState.putString(
            STATE_RESULTS,
            resultText.text.toString()
        )

        super.onSaveInstanceState(outState)
    }

    override fun onDestroy() {
        closed = true
        worker.shutdownNow()
        super.onDestroy()
    }

    companion object {
        private const val STATE_QUERY = "free_research_query"
        private const val STATE_RESULTS = "free_research_results"
    }
}
