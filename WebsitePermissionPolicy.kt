package com.agentsimulation.engine

import java.net.URI
import java.util.Locale

/**
 * Central permission checks for registered websites.
 *
 * Public reading does not require an account grant.
 * Account access requires a valid, short-lived grant.
 * External side effects require a separate owner approval.
 */
class WebsitePermissionPolicy {

    fun evaluate(
        profile: WebsiteProfile,
        action: WebsiteAction,
        grant: WebsiteAccessGrant?,
        now: Long = System.currentTimeMillis()
    ): WebsiteAccessDecision {

        if (!profile.enabled) {
            return denied("This website is disabled in the registry.")
        }

        if (action !in profile.allowedActions) {
            return denied("This action is not permitted for this website.")
        }

        if (action == WebsiteAction.READ_PUBLIC) {
            return WebsiteAccessDecision(
                allowed = true,
                requiresOwnerApproval = false,
                reason = "Public reading is permitted."
            )
        }

        if (grant == null) {
            return denied("A temporary website access grant is required.")
        }

        if (grant.siteId != profile.siteId) {
            return denied("The access grant belongs to a different website.")
        }

        if (now < grant.issuedAt || now >= grant.expiresAt) {
            return denied("The website access grant has expired or is invalid.")
        }

        if (action !in grant.permittedActions) {
            return denied("The access grant does not include this action.")
        }

        if (action in OWNER_APPROVAL_ACTIONS &&
            action !in grant.ownerApprovedActions
        ) {
            return WebsiteAccessDecision(
                allowed = false,
                requiresOwnerApproval = true,
                reason = "This action requires explicit owner approval."
            )
        }

        return WebsiteAccessDecision(
            allowed = true,
            requiresOwnerApproval = false,
            reason = "The temporary access grant permits this action."
        )
    }

    fun isUrlAllowed(
        profile: WebsiteProfile,
        url: String
    ): Boolean {
        if (!profile.enabled) return false

        val uri = try {
            URI(url)
        } catch (_: Exception) {
            return false
        }

        if (!uri.scheme.equals("https", true)) return false
        if (uri.host.isNullOrBlank()) return false
        if (uri.userInfo != null) return false
        if (uri.port != -1 && uri.port != 443) return false

        val host = uri.host.lowercase(Locale.ROOT)

        return profile.allowedDomains.any { allowed ->
            val domain = allowed.lowercase(Locale.ROOT)

            host == domain || host.endsWith(".$domain")
        }
    }

    fun requiresOwnerApproval(
        action: WebsiteAction
    ): Boolean {
        return action in OWNER_APPROVAL_ACTIONS
    }

    private fun denied(reason: String) =
        WebsiteAccessDecision(
            allowed = false,
            requiresOwnerApproval = false,
            reason = reason
        )

    companion object {
        private val OWNER_APPROVAL_ACTIONS = setOf(
            WebsiteAction.PUBLISH,
            WebsiteAction.SEND_MESSAGE,
            WebsiteAction.PURCHASE,
            WebsiteAction.MODIFY_ACCOUNT
        )
    }
}
