
package com.agentsimulation.engine

import android.app.Activity
import androidx.appcompat.app.AlertDialog

/**
 * Presents explicit owner approval for sensitive website actions.
 *
 * Grants are short-lived and held in memory. They are not persisted.
 * This is an application-level approval mechanism, not a security
 * boundary against modified or hostile application code.
 */
class WebsiteApprovalManager(
    private val controller: WebsiteAccessController
) {

    fun requestApproval(
        activity: Activity,
        profile: WebsiteProfile,
        action: WebsiteAction,
        callback: (WebsiteAccessGrant?) -> Unit
    ) {
        if (!profile.enabled) {
            callback(null)
            return
        }

        if (action !in profile.allowedActions) {
            callback(null)
            return
        }

        if (!controller.policy.requiresOwnerApproval(action)) {
            callback(null)
            return
        }

        val description = when (action) {
            WebsiteAction.PUBLISH ->
                "The agent is requesting permission to publish content."

            WebsiteAction.SEND_MESSAGE ->
                "The agent is requesting permission to send a message."

            WebsiteAction.PURCHASE ->
                "The agent is requesting permission to make a purchase."

            WebsiteAction.MODIFY_ACCOUNT ->
                "The agent is requesting permission to modify account settings."

            else ->
                "This action does not use the sensitive-action approval flow."
        }

        AlertDialog.Builder(activity)
            .setTitle("Owner approval required")
            .setMessage(
                "${profile.displayName}\n\n" +
                    description +
                    "\n\nApproving grants permission for this action only. " +
                    "It does not automatically execute the action."
            )
            .setNegativeButton("Deny") { _, _ ->
                controller.auditLog.record(
                    profile.siteId,
                    "OWNER_APPROVAL_${action.name}",
                    "DENIED",
                    "Owner denied the requested action."
                )
                callback(null)
            }
            .setPositiveButton("Approve") { _, _ ->
                val now = System.currentTimeMillis()

                val grant = WebsiteAccessGrant(
                    siteId = profile.siteId,
                    permittedActions = setOf(action),
                    ownerApprovedActions = setOf(action),
                    issuedAt = now,
                    expiresAt = now + GRANT_LIFETIME_MS
                )

                controller.auditLog.record(
                    profile.siteId,
                    "OWNER_APPROVAL_${action.name}",
                    "APPROVED",
                    "Owner approved a short-lived single-action grant."
                )

                callback(grant)
            }
            .setOnCancelListener {
                callback(null)
            }
            .show()
    }

    companion object {
        private const val GRANT_LIFETIME_MS = 5 * 60 * 1000L
    }
}
