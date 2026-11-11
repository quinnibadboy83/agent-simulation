package com.agentsimulation.engine

import android.app.Activity
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.ArrayAdapter
import android.widget.TextView
import android.widget.Toast

/**
 * Owner-facing website registry and permission management screen.
 *
 * This screen manages configuration and approval only.
 * Browser automation is not implemented by this activity.
 */
class WebsiteAccessActivity : Activity() {

    private lateinit var page: LinearLayout
    private lateinit var controller: WebsiteAccessController
    private lateinit var approvalManager: WebsiteApprovalManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        controller = WebsiteAccessController(applicationContext)
        approvalManager = WebsiteApprovalManager(controller)

        val padding = (20 * resources.displayMetrics.density).toInt()

        page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
            gravity = Gravity.TOP
        }

        val title = TextView(this).apply {
            text = "Website Access"
            textSize = 26f
        }

        val explanation = TextView(this).apply {
            text =
                "Register websites that Kairnex may be allowed to use. " +
                "Website registration does not grant unrestricted access. " +
                "Sensitive actions require separate owner approval."
            textSize = 14f
        }

        val addButton = Button(this).apply {
            text = "Register a website"
            setOnClickListener { showAddWebsiteDialog() }
        }

        val auditButton = Button(this).apply {
            text = "View website audit history"
            setOnClickListener { showAuditHistory() }
        }

        val refreshButton = Button(this).apply {
            text = "Refresh website list"
            setOnClickListener { refreshWebsites() }
        }

        page.addView(title)
        page.addView(explanation)
        page.addView(addButton)
        page.addView(refreshButton)
        page.addView(auditButton)
        page.addView(spacer(12))

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
        refreshWebsites()
    }

    override fun onResume() {
        super.onResume()

        if (::controller.isInitialized && ::page.isInitialized) {
            refreshWebsites()
        }
    }

    private fun refreshWebsites() {
        // Preserve the three permanent controls at the top.
        while (page.childCount > 6) {
            page.removeViewAt(6)
        }

        val profiles = controller.registry.getAll()

        if (profiles.isEmpty()) {
            page.addView(
                TextView(this).apply {
                    text = "No websites registered yet."
                    textSize = 16f
                }
            )
            return
        }

        profiles.forEach { profile ->
            page.addView(spacer(14))

            val divider = TextView(this).apply {
                text = "--------------------------------"
                textSize = 14f
            }

            val details = TextView(this).apply {
                text = WebsiteAccessAdapter.describe(
                    profile,
                    controller.credentialVault.hasCredentials(profile.siteId)
                )
                textSize = 14f
                setTextIsSelectable(true)
            }

            val credentialsButton = Button(this).apply {
                text = "Manage encrypted credentials"
                setOnClickListener {
                    startActivity(
                        android.content.Intent(
                            this@WebsiteAccessActivity,
                            WebsiteCredentialActivity::class.java
                        ).putExtra(
                            WebsiteCredentialActivity.EXTRA_SITE_ID,
                            profile.siteId
                        )
                    )
                }
            }

            val enableButton = Button(this).apply {
                text = if (profile.enabled) {
                    "Disable website"
                } else {
                    "Enable website"
                }

                setOnClickListener {
                    controller.setWebsiteEnabled(
                        profile.siteId,
                        !profile.enabled
                    )
                    refreshWebsites()
                }
            }

            val approvalButton = Button(this).apply {
                text = "Review sensitive-action approval"

                isEnabled = profile.enabled &&
                    profile.allowedActions.any {
                        controller.policy.requiresOwnerApproval(it)
                    }

                setOnClickListener {
                    showApprovalOptions(profile)
                }
            }

            val deleteButton = Button(this).apply {
                text = "Delete website"

                setOnClickListener {
                    confirmDelete(profile)
                }
            }

            page.addView(divider)
            page.addView(details)
            page.addView(credentialsButton)
            page.addView(enableButton)
            page.addView(approvalButton)
            page.addView(deleteButton)
        }
    }

    private fun showAddWebsiteDialog() {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 8, 24, 8)
        }

        val nameInput = EditText(this).apply {
            hint = "Website name"
        }

        val urlInput = EditText(this).apply {
            hint = "HTTPS address, e.g. https://example.com"
        }

        val methodSpinner = Spinner(this)
        val methods = WebsiteAccessMethod.values().toList()

        methodSpinner.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            methods.map { it.name }
        )

        val actionChecks = mutableMapOf<WebsiteAction, CheckBox>()

        WebsiteAction.values().forEach { action ->
            val check = CheckBox(this).apply {
                text = WebsiteAccessAdapter.actionLabel(action)
                isChecked = action == WebsiteAction.READ_PUBLIC
            }

            actionChecks[action] = check
            layout.addView(check)
        }

        layout.addView(nameInput)
        layout.addView(urlInput)
        layout.addView(TextView(this).apply {
            text = "Access method"
        })
        layout.addView(methodSpinner)

        val scroll = ScrollView(this).apply {
            addView(layout)
        }

        val dialog = android.app.AlertDialog.Builder(this)
            .setTitle("Register website")
            .setView(scroll)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Register", null)
            .create()

        dialog.setOnShowListener {
            dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener {
                    val actions = actionChecks
                        .filterValues { it.isChecked }
                        .keys
                        .toSet()

                    try {
                        val profile = controller.registerWebsite(
                            displayName = nameInput.text.toString(),
                            baseUrl = urlInput.text.toString(),
                            accessMethod = methods[methodSpinner.selectedItemPosition],
                            allowedActions = actions
                        )

                        Toast.makeText(
                            this,
                            "${profile.displayName} registered.",
                            Toast.LENGTH_SHORT
                        ).show()

                        dialog.dismiss()
                        refreshWebsites()

                    } catch (error: Exception) {
                        Toast.makeText(
                            this,
                            error.message ?: "Website registration failed.",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }
        }

        dialog.show()
    }

    private fun showApprovalOptions(profile: WebsiteProfile) {
        val actions = profile.allowedActions
            .filter { controller.policy.requiresOwnerApproval(it) }

        if (actions.isEmpty()) {
            Toast.makeText(
                this,
                "No sensitive actions are enabled for this website.",
                Toast.LENGTH_SHORT
            ).show()
            return
        }

        val labels = actions.map {
            WebsiteAccessAdapter.actionLabel(it)
        }.toTypedArray()

        android.app.AlertDialog.Builder(this)
            .setTitle("Choose action to review")
            .setItems(labels) { _, which ->
                approvalManager.requestApproval(
                    activity = this,
                    profile = profile,
                    action = actions[which]
                ) { grant ->
                    if (grant == null) {
                        Toast.makeText(
                            this,
                            "No approval grant issued.",
                            Toast.LENGTH_SHORT
                        ).show()
                    } else {
                        Toast.makeText(
                            this,
                            "Approved for this action only. Grant expires in five minutes. No website action has been executed.",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun confirmDelete(profile: WebsiteProfile) {
        android.app.AlertDialog.Builder(this)
            .setTitle("Delete website?")
            .setMessage(
                "This removes ${profile.displayName} and its stored credentials from the registry."
            )
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Delete") { _, _ ->
                controller.deleteWebsite(profile.siteId)
                refreshWebsites()
            }
            .show()
    }

    private fun showAuditHistory() {
        val events = controller.auditLog.getRecent(100)

        val content = if (events.isEmpty()) {
            "No website access events recorded."
        } else {
            buildString {
                events.forEachIndexed { index, event ->
                    appendLine("${index + 1}. ${event.action}")
                    appendLine("Outcome: ${event.outcome}")
                    appendLine("Website ID: ${event.siteId}")
                    appendLine("Detail: ${event.detail}")
                    appendLine("Time: ${java.util.Date(event.timestamp)}")
                    appendLine()
                }
            }
        }

        val view = TextView(this).apply {
            text = content
            textSize = 13f
            setTextIsSelectable(true)
            setPadding(24, 16, 24, 16)
        }

        val scroll = ScrollView(this).apply {
            addView(
                view,
                ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
            )
        }

        android.app.AlertDialog.Builder(this)
            .setTitle("Website audit history")
            .setView(scroll)
            .setPositiveButton("Close", null)
            .show()
    }

    private fun spacer(heightDp: Int): TextView {
        return TextView(this).apply {
            height = (
                heightDp * resources.displayMetrics.density
            ).toInt()
        }
    }
}
