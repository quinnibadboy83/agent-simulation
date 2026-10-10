
package com.agentsimulation.engine

import android.app.Activity
import android.os.Bundle
import android.content.Intent
import android.graphics.Typeface
import android.net.Uri
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

class MainActivity : Activity() {

    private lateinit var modelStatus: TextView
    private lateinit var runtimeStatus: TextView
    private lateinit var diagnosticsStatus: TextView

    private val preferences by lazy {
        getSharedPreferences("engine_settings", MODE_PRIVATE)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

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
        }

        runtimeStatus = TextView(this).apply {
            textSize = 16f
        }

        diagnosticsStatus = TextView(this).apply {
            text = "Ready for initialisation."
            textSize = 14f
        }

        page.addView(title)
        page.addView(subtitle)
        page.addView(spacer(24))
        page.addView(modelStatus)
        page.addView(spacer(12))
        page.addView(runtimeStatus)
        page.addView(spacer(24))

        val chooseModelButton = Button(this).apply {
            text = "Choose local GGUF model"
            setOnClickListener {
                chooseModel()
            }
        }

        val diagnosticsButton = Button(this).apply {
            text = "Engine diagnostics"
            setOnClickListener {
                diagnosticsStatus.text = buildString {
                    appendLine("Application: running")
                    appendLine("Android API: ${android.os.Build.VERSION.SDK_INT}")
                    appendLine("Device: ${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}")
                    appendLine("Model selected: ${selectedModelUri() != null}")
                    append("Local inference: not integrated yet")
                }
            }
        }

        page.addView(chooseModelButton)
        page.addView(diagnosticsButton)
        page.addView(spacer(16))
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
        refreshStatus()
    }

    private fun spacer(heightDp: Int): TextView {
        return TextView(this).apply {
            height = (heightDp * resources.displayMetrics.density).toInt()
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

        val uri: Uri = data?.data ?: return

        try {
            val flags = data.flags and
                (Intent.FLAG_GRANT_READ_URI_PERMISSION or
                    Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)

            contentResolver.takePersistableUriPermission(
                uri,
                flags and Intent.FLAG_GRANT_READ_URI_PERMISSION
            )
        } catch (_: SecurityException) {
            // Some document providers do not grant persistent access.
        }

        preferences.edit()
            .putString(KEY_MODEL_URI, uri.toString())
            .apply()

        refreshStatus()
    }

    private fun selectedModelUri(): Uri? {
        val saved = preferences.getString(KEY_MODEL_URI, null)
        return saved?.let { Uri.parse(it) }
    }

    private fun refreshStatus() {
        val uri = selectedModelUri()

        modelStatus.text = if (uri == null) {
            "Local model: Not selected"
        } else {
            "Local model: Selected\n${uri.lastPathSegment ?: "Model file"}"
        }

        runtimeStatus.text =
            "Agent runtime: Integration pending\n" +
            "Inference engine: Not connected yet"
    }

    companion object {
        private const val REQUEST_MODEL = 1001
        private const val KEY_MODEL_URI = "selected_model_uri"
    }
}
