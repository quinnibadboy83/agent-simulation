
package com.agentsimulation.engine

import android.app.Activity
import android.content.Intent
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.util.UUID

class MainActivity : Activity() {

    private lateinit var memoryStore: AgentMemoryStore
    private lateinit var approvalGate: CreatorApprovalGate
    private lateinit var runtime: LocalAgentRuntime

    private lateinit var modelStatus: TextView
    private lateinit var diagnosticsStatus: TextView
    private lateinit var conversationContainer: LinearLayout
    private lateinit var approvalsContainer: LinearLayout
    private lateinit var messageInput: EditText

    private val preferences by lazy {
        getSharedPreferences("engine_settings", MODE_PRIVATE)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        memoryStore = AgentMemoryStore(applicationContext)
        approvalGate = CreatorApprovalGate(memoryStore)
        runtime = LocalAgentRuntime(memoryStore)

        buildInterface()
        refreshAll()
    }

    private fun buildInterface() {
        val pagePadding = dp(16)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pagePadding, pagePadding, pagePadding, pagePadding)
        }

        val scrollContent = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        val title = TextView(this).apply {
            text = "Agent Simulation Engine"
            textSize = 25f
            setTypeface(null, Typeface.BOLD)
        }

        val subtitle = TextView(this).apply {
            text = "Portable, local-first agent platform"
            textSize = 14f
        }

        modelStatus = TextView(this).apply {
            textSize = 14f
        }

        scrollContent.addView(title)
        scrollContent.addView(subtitle)
        scrollContent.addView(spacer(12))
        scrollContent.addView(modelStatus)
        scrollContent.addView(sectionTitle("CONVERSATION"))
        
        conversationContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        scrollContent.addView(conversationContainer)

        scrollContent.addView(sectionTitle("CREATOR APPROVAL QUEUE"))

        approvalsContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        scrollContent.addView(approvalsContainer)

        diagnosticsStatus = TextView(this).apply {
            text = "Diagnostics have not been run."
            textSize = 13f
        }
        scrollContent.addView(sectionTitle("DIAGNOSTICS"))
        scrollContent.addView(diagnosticsStatus)

        val scrollView = ScrollView(this).apply {
            isFillViewport = false
            addView(
                scrollContent,
                ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
            )
        }

        root.addView(
            scrollView,
            LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1f
            )
        )

        messageInput = EditText(this).apply {
            hint = "Message Boss or describe an action to review"
            minLines = 1
            maxLines = 4
            textSize = 15f
        }

        val inputRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

        inputRow.addView(
            messageInput,
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        )

        val sendButton = Button(this).apply {
            text = "Send"
            setOnClickListener { sendMessage() }
        }
        inputRow.addView(sendButton)

        root.addView(inputRow)

        val actionRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }

        val modelButton = Button(this).apply {
            text = "Choose Model"
            setOnClickListener { chooseModel() }
        }

        val approvalButton = Button(this).apply {
            text = "Request Approval"
            setOnClickListener { requestApproval() }
        }

        actionRow.addView(
            modelButton,
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        )
        actionRow.addView(
            approvalButton,
            LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        )
        root.addView(actionRow)

        val diagnosticsButton = Button(this).apply {
            text = "Run Diagnostics"
            setOnClickListener { runDiagnostics() }
        }
        root.addView(diagnosticsButton)

        setContentView(root)
    }

    private fun sendMessage() {
        val text = messageInput.text?.toString()?.trim().orEmpty()
        if (text.isBlank()) return

        memoryStore.appendMessage(
            ChatMessage(
                role = "user",
                content = text
            )
        )

        messageInput.setText("")

        val response = runtime.handleUserMessage(
            rawText = text,
            selectedModelUri = selectedModelUri()?.toString()
        )

        memoryStore.appendMessage(response)
        refreshAll()
    }

    private fun requestApproval() {
        val description = messageInput.text?.toString()?.trim().orEmpty()

        if (description.isBlank()) {
            diagnosticsStatus.text =
                "Enter a clear description of the proposed action first."
            return
        }

        val request = approvalGate.requestApproval(description)

        if (request == null) {
            diagnosticsStatus.text =
                "Request not created. Check that the description is valid " +
                    "and no longer than 2000 characters."
            return
        }

        messageInput.setText("")

        memoryStore.appendMessage(
            ChatMessage(
                role = "system",
                content = "Approval request created: ${request.description}\n" +
                    "No external action has been executed."
            )
        )

        refreshAll()
        diagnosticsStatus.text =
            "Request queued for your decision. No external action was executed."
    }

    private fun resolveApproval(requestId: String, approve: Boolean) {
        val resolved = if (approve) {
            approvalGate.approve(requestId)
        } else {
            approvalGate.deny(requestId)
        }

        if (resolved == null) {
            diagnosticsStatus.text =
                "Decision not applied. The request may already have been resolved."
            refreshAll()
            return
        }

        val decision = if (approve) "APPROVED" else "DENIED"

        memoryStore.appendMessage(
            ChatMessage(
                role = "system",
                content = "Creator decision: $decision\n" +
                    "Proposed action: ${resolved.description}\n" +
                    "This shell records the decision only. " +
                    "No external action was executed."
            )
        )

        refreshAll()
        diagnosticsStatus.text =
            "$decision recorded. No external action was executed."
    }

    private fun refreshAll() {
        refreshModelStatus()
        refreshConversation()
        refreshApprovals()
    }

    private fun refreshModelStatus() {
        val uri = selectedModelUri()

        modelStatus.text = if (uri == null) {
            "Local model file: Not selected\n" +
                "Inference: Not connected yet"
        } else {
            "Model file selected: ${uri.lastPathSegment ?: "Selected file"}\n" +
                "Inference: File selection only; model is not running yet"
        }
    }

    private fun refreshConversation() {
        conversationContainer.removeAllViews()

        val messages = memoryStore.loadMessages()

        if (messages.isEmpty()) {
            conversationContainer.addView(
                bodyText(
                    "Boss: The Android shell is ready. Type 'help' or 'status'.\n" +
                        "This version stores conversation history locally. " +
                        "Native model inference is not connected yet."
                )
            )
            return
        }

        messages.forEach { message ->
            val role = message.role.uppercase()
            conversationContainer.addView(
                bodyText("$role\n${message.content}")
            )
            conversationContainer.addView(spacer(6))
        }
    }

    private fun refreshApprovals() {
        approvalsContainer.removeAllViews()

        val requests = memoryStore.loadApprovals()

        if (requests.isEmpty()) {
            approvalsContainer.addView(
                bodyText("No approval requests yet.")
            )
            return
        }

        requests.forEach { request ->
            val entry = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(8), dp(8), dp(8), dp(8))
            }

            entry.addView(
                bodyText(
                    "Status: ${request.status}\n" +
                        "Action: ${request.description}"
                )
            )

            if (request.status == ApprovalRequest.STATUS_PENDING) {
                val buttons = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                }

                val approveButton = Button(this).apply {
                    text = "Approve"
                    setOnClickListener {
                        resolveApproval(request.id, true)
                    }
                }

                val denyButton = Button(this).apply {
                    text = "Deny"
                    setOnClickListener {
                        resolveApproval(request.id, false)
                    }
                }

                buttons.addView(
                    approveButton,
                    LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                    )
                )
                buttons.addView(
                    denyButton,
                    LinearLayout.LayoutParams(
                        0,
                        ViewGroup.LayoutParams.WRAP_CONTENT,
                        1f
                    )
                )

                entry.addView(buttons)
            }

            approvalsContainer.addView(entry)
            approvalsContainer.addView(spacer(6))
        }
    }

    private fun chooseModel() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
        }

        @Suppress("DEPRECATION")
        startActivityForResult(intent, REQUEST_MODEL)
    }

    @Deprecated("Uses the activity result callback for compatibility")
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
            val readPermission =
                data.flags and Intent.FLAG_GRANT_READ_URI_PERMISSION

            if (readPermission != 0) {
                contentResolver.takePersistableUriPermission(
                    uri,
                    readPermission
                )
            }
        } catch (_: Exception) {
            // Some document providers do not support persistent permissions.
        }

        preferences.edit()
            .putString(KEY_MODEL_URI, uri.toString())
            .apply()

        refreshAll()
        diagnosticsStatus.text =
            "File selected. This does not load or execute the model."
    }

    private fun selectedModelUri(): Uri? {
        val saved = preferences.getString(KEY_MODEL_URI, null)
        return saved?.let { Uri.parse(it) }
    }

    private fun runDiagnostics() {
        diagnosticsStatus.text = buildString {
            appendLine("Application: running")
            appendLine("Android API: ${Build.VERSION.SDK_INT}")
            appendLine("Device: ${Build.MANUFACTURER} ${Build.MODEL}")
            appendLine("Conversation entries: ${memoryStore.loadMessages().size}")
            appendLine("Pending approvals: ${memoryStore.pendingApprovalCount()}")
            appendLine("Local persistent memory: available")
            appendLine("Model selected: ${selectedModelUri() != null}")
            appendLine("Native inference: not integrated")
            appendLine("Python engine connection: not integrated")
            append("External action execution: not available in this shell")
        }
    }

    private fun sectionTitle(text: String): TextView {
        return TextView(this).apply {
            this.text = text
            textSize = 13f
            setTypeface(null, Typeface.BOLD)
            setPadding(0, dp(16), 0, dp(6))
        }
    }

    private fun bodyText(text: String): TextView {
        return TextView(this).apply {
            this.text = text
            textSize = 14f
            setPadding(dp(6), dp(6), dp(6), dp(6))
        }
    }

    private fun spacer(heightDp: Int): TextView {
        return TextView(this).apply {
            height = dp(heightDp)
        }
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    companion object {
        private const val REQUEST_MODEL = 1001
        private const val KEY_MODEL_URI = "selected_model_uri"
    }
}
