package com.agentsimulation.engine

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.net.URI
import java.util.Locale
import java.util.UUID

/**
 * Stores the user's manually registered website profiles.
 *
 * Website configuration is not secret. Credentials belong in
 * WebsiteCredentialVault and must never be stored here.
 */
class WebsiteAccessRegistry(context: Context) {

    private val preferences = context.applicationContext
        .getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    @Synchronized
    fun register(profile: WebsiteProfile): WebsiteProfile {
        val clean = validateAndNormalise(profile)
        val existing = readProfiles().toMutableList()

        val index = existing.indexOfFirst {
            it.siteId == clean.siteId
        }

        val stored = if (index >= 0) {
            clean.copy(
                createdAt = existing[index].createdAt,
                updatedAt = System.currentTimeMillis()
            ).also {
                existing[index] = it
            }
        } else {
            clean.copy(
                createdAt = System.currentTimeMillis(),
                updatedAt = System.currentTimeMillis()
            ).also {
                existing.add(it)
            }
        }

        writeProfiles(existing)
        return stored
    }

    @Synchronized
    fun create(
        displayName: String,
        baseUrl: String,
        accessMethod: WebsiteAccessMethod,
        allowedActions: Set<WebsiteAction>,
        enabled: Boolean = true
    ): WebsiteProfile {
        val host = extractHost(baseUrl)

        val profile = WebsiteProfile(
            siteId = UUID.randomUUID().toString(),
            displayName = displayName.trim(),
            baseUrl = normaliseBaseUrl(baseUrl),
            accessMethod = accessMethod,
            allowedDomains = listOf(host),
            allowedActions = allowedActions,
            enabled = enabled,
            createdAt = System.currentTimeMillis(),
            updatedAt = System.currentTimeMillis()
        )

        return register(profile)
    }

    @Synchronized
    fun get(siteId: String): WebsiteProfile? {
        return readProfiles().firstOrNull {
            it.siteId == siteId
        }
    }

    @Synchronized
    fun getAll(): List<WebsiteProfile> {
        return readProfiles().sortedBy {
            it.displayName.lowercase(Locale.ROOT)
        }
    }

    @Synchronized
    fun getEnabled(): List<WebsiteProfile> {
        return getAll().filter { it.enabled }
    }

    @Synchronized
    fun setEnabled(
        siteId: String,
        enabled: Boolean
    ): Boolean {
        val profiles = readProfiles().toMutableList()
        val index = profiles.indexOfFirst {
            it.siteId == siteId
        }

        if (index < 0) return false

        profiles[index] = profiles[index].copy(
            enabled = enabled,
            updatedAt = System.currentTimeMillis()
        )

        writeProfiles(profiles)
        return true
    }

    @Synchronized
    fun delete(siteId: String): Boolean {
        val profiles = readProfiles().toMutableList()
        val removed = profiles.removeAll {
            it.siteId == siteId
        }

        if (removed) {
            writeProfiles(profiles)
        }

        return removed
    }

    @Synchronized
    fun count(): Int = readProfiles().size

    private fun validateAndNormalise(
        profile: WebsiteProfile
    ): WebsiteProfile {
        require(profile.siteId.isNotBlank()) {
            "Website ID cannot be empty."
        }

        require(profile.displayName.isNotBlank()) {
            "Website name cannot be empty."
        }

        require(profile.displayName.length <= 100) {
            "Website name is too long."
        }

        val normalisedUrl = normaliseBaseUrl(profile.baseUrl)
        val baseHost = extractHost(normalisedUrl)

        val domains = profile.allowedDomains
            .map { normaliseDomain(it) }
            .distinct()

        require(domains.isNotEmpty()) {
            "At least one allowed domain is required."
        }

        require(domains.any { domainMatches(baseHost, it) }) {
            "The base website host must be included in allowed domains."
        }

        require(profile.allowedActions.isNotEmpty()) {
            "Select at least one permitted website action."
        }

        return profile.copy(
            displayName = profile.displayName.trim(),
            baseUrl = normalisedUrl,
            allowedDomains = domains
        )
    }

    private fun normaliseBaseUrl(value: String): String {
        val uri = try {
            URI(value.trim())
        } catch (_: Exception) {
            throw IllegalArgumentException("Website address is invalid.")
        }

        require(uri.scheme.equals("https", true)) {
            "Only HTTPS website addresses are accepted."
        }

        require(!uri.host.isNullOrBlank()) {
            "Website address must contain a valid host."
        }

        require(uri.userInfo == null) {
            "Website addresses must not contain embedded credentials."
        }

        require(uri.port == -1 || uri.port == 443) {
            "Only the standard HTTPS port is accepted."
        }

        require(uri.query == null && uri.fragment == null) {
            "Website base address must not contain a query or fragment."
        }

        val host = uri.host.lowercase(Locale.ROOT)
        val path = uri.rawPath
            ?.trimEnd('/')
            .orEmpty()

        return "https://$host$path"
    }

    private fun extractHost(value: String): String {
        return URI(value).host
            ?.lowercase(Locale.ROOT)
            ?: throw IllegalArgumentException("Website host is invalid.")
    }

    private fun normaliseDomain(value: String): String {
        val clean = value.trim()
            .lowercase(Locale.ROOT)
            .removePrefix("https://")
            .removePrefix("http://")
            .trimEnd('/')

        require(clean.isNotBlank()) {
            "Allowed domain cannot be empty."
        }

        require(
            clean.matches(
                Regex("[a-z0-9.-]+")
            ) && !clean.startsWith(".") &&
                !clean.endsWith(".") &&
                ".." !in clean
        ) {
            "Allowed domain is invalid."
        }

        return clean
    }

    private fun domainMatches(
        host: String,
        allowedDomain: String
    ): Boolean {
        return host == allowedDomain ||
            host.endsWith(".$allowedDomain")
    }

    private fun readProfiles(): List<WebsiteProfile> {
        val raw = preferences.getString(KEY_PROFILES, null)
            ?: return emptyList()

        return try {
            val array = JSONArray(raw)
            val profiles = mutableListOf<WebsiteProfile>()

            for (index in 0 until array.length()) {
                val item = array.optJSONObject(index) ?: continue

                val actions = mutableSetOf<WebsiteAction>()
                val actionArray = item.optJSONArray("allowedActions")
                    ?: JSONArray()

                for (actionIndex in 0 until actionArray.length()) {
                    val name = actionArray.optString(actionIndex)

                    runCatching {
                        WebsiteAction.valueOf(name)
                    }.getOrNull()?.let(actions::add)
                }

                val domains = mutableListOf<String>()
                val domainArray = item.optJSONArray("allowedDomains")
                    ?: JSONArray()

                for (domainIndex in 0 until domainArray.length()) {
                    val domain = domainArray.optString(domainIndex)
                    if (domain.isNotBlank()) domains.add(domain)
                }

                val method = runCatching {
                    WebsiteAccessMethod.valueOf(
                        item.optString("accessMethod")
                    )
                }.getOrNull() ?: continue

                val profile = runCatching {
                    WebsiteProfile(
                        siteId = item.getString("siteId"),
                        displayName = item.getString("displayName"),
                        baseUrl = item.getString("baseUrl"),
                        accessMethod = method,
                        allowedDomains = domains,
                        allowedActions = actions,
                        enabled = item.optBoolean("enabled", false),
                        createdAt = item.optLong("createdAt"),
                        updatedAt = item.optLong("updatedAt")
                    )
                }.getOrNull() ?: continue

                profiles.add(profile)
            }

            profiles
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun writeProfiles(profiles: List<WebsiteProfile>) {
        val array = JSONArray()

        profiles.forEach { profile ->
            array.put(
                JSONObject().apply {
                    put("siteId", profile.siteId)
                    put("displayName", profile.displayName)
                    put("baseUrl", profile.baseUrl)
                    put("accessMethod", profile.accessMethod.name)
                    put("allowedDomains", JSONArray(profile.allowedDomains))
                    put(
                        "allowedActions",
                        JSONArray(profile.allowedActions.map { it.name })
                    )
                    put("enabled", profile.enabled)
                    put("createdAt", profile.createdAt)
                    put("updatedAt", profile.updatedAt)
                }
            )
        }

        check(
            preferences.edit()
                .putString(KEY_PROFILES, array.toString())
                .commit()
        ) {
            "Could not save website registry."
        }
    }

    companion object {
        private const val PREFERENCES_NAME =
            "agent_website_registry"

        private const val KEY_PROFILES =
            "registered_websites"
    }
}
