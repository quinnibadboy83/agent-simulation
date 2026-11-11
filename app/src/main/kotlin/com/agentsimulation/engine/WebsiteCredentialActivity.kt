
package com.agentsimulation.engine

import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast

/**
 * Secure credential entry screen.
 *
 * Existing credentials are never loaded into the input fields.
 * The user must enter replacement values explicitly.
 */
class WebsiteCredentialActivity : Activity() {

    private lateinit var loginInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var tokenInput: EditText
    private lateinit var statusText: TextView

    private lateinit var controller: WebsiteAccessController

    private var siteId: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        controller = WebsiteAccessController(applicationContext)
        siteId = intent.getStringExtra(EXTRA_SITE_ID).orEmpty()

        val profile = controller.registry.get(siteId)

        if (profile == null) {
            Toast.makeText(
                this,
                "Website registration was not found.",
                Toast.LENGTH_LONG
            ).show()
            finish()
            return
        }

        val padding = (20 * resources.displayMetrics.density).toInt()

        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }

        val title = TextView(this).apply {
            text = "Credentials — ${profile.displayName}"
            textSize = 22f
        }

        val explanation = TextView(this).apply {
            text =
                "Credentials are encrypted using Android Keystore. " +
                "Saved secrets are never displayed again on this screen " +
                "and must never be copied into agent prompts or memory."
            textSize = 14f
        }

        loginInput = EditText(this).apply {
            hint = "Login identifier / email"
            inputType = InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
        }

        passwordInput = EditText(this).apply {
            hint = "Password"
            inputType = InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_VARIATION_PASSWORD
        }

        tokenInput = EditText(this).apply {
            hint = "API token (optional)"
            inputType = InputType.TYPE_CLASS_TEXT or
                InputType.TYPE_TEXT_VARIATION_PASSWORD
        }

        statusText = TextView(this).apply {
            textSize = 14f
            text = if (controller.credentialVault.hasCredentials(siteId)) {
                "Encrypted credentials already exist. Enter new values to replace them."
            } else {
                "No credentials are currently stored."
            }
        }

        val saveButton = Button(this).apply {
            text = "Encrypt and save credentials"

            setOnClickListener {
                saveCredentials()
            }
        }

        val deleteButton = Button(this).apply {
            text = "Delete stored credentials"

            setOnClickListener {
                deleteCredentials()
            }
        }

        val backButton = Button(this).apply {
            text = "Back"

            setOnClickListener {
                finish()
            }
        }

        page.addView(title)
        page.addView(explanation)
        page.addView(loginInput)
        page.addView(passwordInput)
        page.addView(tokenInput)
        page.addView(saveButton)
        page.addView(deleteButton)
        page.addView(statusText)
        page.addView(backButton)

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
    }

    private fun saveCredentials() {
        val login = loginInput.text.toString()
        val password = passwordInput.text.toString()
        val token = tokenInput.text.toString()

        val credentials = WebsiteCredentials(
            loginIdentifier = login,
            password = password,
            apiToken = token
        )

        try {
            controller.credentialVault.save(siteId, credentials)
            controller.recordCredentialSave(siteId)

            // Clear all secret input fields immediately after saving.
            loginInput.text.clear()
            passwordInput.text.clear()
            tokenInput.text.clear()

            statusText.text =
                "Credentials encrypted and saved. Secret fields have been cleared."

            Toast.makeText(
                this,
                "Credentials saved securely.",
                Toast.LENGTH_SHORT
            ).show()

        } catch (error: Exception) {
            statusText.text =
                "Credential save failed: " +
                    (error.message ?: error.javaClass.simpleName)
        }
    }

    private fun deleteCredentials() {
        try {
            controller.credentialVault.delete(siteId)
            controller.recordCredentialDelete(siteId)

            loginInput.text.clear()
            passwordInput.text.clear()
            tokenInput.text.clear()

            statusText.text = "Stored credentials deleted."

        } catch (error: Exception) {
            statusText.text =
                "Credential deletion failed: " +
                    (error.message ?: error.javaClass.simpleName)
        }
    }

    companion object {
        const val EXTRA_SITE_ID = "website_access_site_id"
    }
}
