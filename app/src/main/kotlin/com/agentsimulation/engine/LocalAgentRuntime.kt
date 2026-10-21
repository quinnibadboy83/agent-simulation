
package com.agentsimulation.engine

/**
 * Temporary local conversation handler.
 *
 * This is not an LLM and does not load or run a GGUF model.
 * It provides basic status/help responses until native inference is connected.
 */
class LocalAgentRuntime(
    private val memoryStore: AgentMemoryStore
) {

    fun handleUserMessage(
        rawText: String,
        selectedModelUri: String?
    ): ChatMessage {
        val message = rawText.trim()

        val response = when (message.lowercase()) {
            "help", "commands" -> helpResponse()

            "status", "report", "overview" -> statusResponse(
                selectedModelUri
            )

            "memory", "show memory" -> memoryResponse()

            else -> buildString {
                appendLine("Boss received your message.")
                appendLine()
                appendLine("Your message has been saved to local app memory.")
                appendLine(
                    "Conversation entries stored: ${memoryStore.loadMessages().size}"
                )
                appendLine()

                if (selectedModelUri == null) {
                    appendLine("No local model file has been selected.")
                } else {
                    appendLine(
                        "A model file has been selected, but it is not " +
                            "loaded or executed by this runtime yet."
                    )
                }

                appendLine()
                append(
                    "Native model inference and specialist-agent delegation " +
                        "are still to be integrated. This response is from " +
                        "the temporary built-in responder, not an AI model."
                )
            }
        }

        return ChatMessage(
            role = "assistant",
            content = response
        )
    }

    private fun helpResponse(): String {
        return """
            Agent Simulation Engine — available shell commands

            status
            Shows the current app and model-integration status.

            memory
            Shows the number of locally stored conversation entries.

            help
            Shows these commands.

            Other messages are saved locally and receive a temporary
            built-in response until local model inference is integrated.

            Protected actions must be submitted for creator approval.
            This shell does not execute external actions.
        """.trimIndent()
    }

    private fun statusResponse(selectedModelUri: String?): String {
        val modelStatus = if (selectedModelUri == null) {
            "No model file selected."
        } else {
            "A model file is selected, but native inference is not connected."
        }

        return """
            Agent Simulation Engine status

            App shell: running
            Local conversation memory: available
            Creator approval queue: available
            Local model: $modelStatus
            Native inference: not integrated
            Python engine connection: not integrated
            External action execution: not available in this shell

            Existing Python engine files have not been replaced by this
            Android runtime.
        """.trimIndent()
    }

    private fun memoryResponse(): String {
        val count = memoryStore.loadMessages().size
        val pending = memoryStore.pendingApprovalCount()

        return """
            Local memory report

            Stored conversation entries: $count
            Pending creator approvals: $pending

            This memory belongs to this Android app installation.
            It is not yet synchronised with the Python engine's memory.json.
        """.trimIndent()
    }
}
