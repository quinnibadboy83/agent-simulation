package com.agentsimulation.engine

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Encrypted, device-local storage for website credentials.
 *
 * AES-256-GCM encryption uses a key held in Android Keystore.
 * Encrypted records are stored separately from website profiles.
 *
 * Never put returned credentials into an agent prompt, memory record,
 * audit event, or ordinary application log.
 */
class WebsiteCredentialVault(
    context: Context,
    private val registry: WebsiteAccessRegistry
) {

    private val preferences = context.applicationContext
        .getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    @Synchronized
    fun save(
        siteId: String,
        credentials: WebsiteCredentials
    ) {
        validateSiteId(siteId)

        require(registry.get(siteId) != null) {
            "Register this website before saving its credentials."
        }

        require(!credentials.isEmpty()) {
            "At least one credential field must be provided."
        }

        val json = JSONObject().apply {
            put("loginIdentifier", credentials.loginIdentifier)
            put("password", credentials.password)
            put("apiToken", credentials.apiToken)

            val extras = JSONObject()
            credentials.extraFields.forEach { (key, value) ->
                require(key.isNotBlank() && key.length <= 80) {
                    "Credential field name is invalid."
                }
                require(value.length <= MAX_FIELD_LENGTH) {
                    "A credential field is too long."
                }
                extras.put(key, value)
            }

            put("extraFields", extras)
        }.toString()

        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateSecretKey())

        val encrypted = cipher.doFinal(
            json.toByteArray(StandardCharsets.UTF_8)
        )

        val packed = cipher.iv + encrypted
        val encoded = Base64.encodeToString(
            packed,
            Base64.NO_WRAP
        )

        check(
            preferences.edit()
                .putString(storageKey(siteId), encoded)
                .commit()
        ) {
            "Could not securely save website credentials."
        }
    }

    /**
     * Credentials can only be retrieved for a registered website
     * when a valid grant permits account access.
     *
     * This API is for trusted integrations only. It must never pass
     * credentials to an LLM, agent prompt, or ordinary application log.
     */
    @Synchronized
    fun getForAuthorizedUse(
        siteId: String,
        grant: WebsiteAccessGrant,
        policy: WebsitePermissionPolicy
    ): WebsiteCredentials? {
        validateSiteId(siteId)

        val profile = registry.get(siteId) ?: return null

        val decision = policy.evaluate(
            profile = profile,
            action = WebsiteAction.READ_ACCOUNT,
            grant = grant
        )

        check(decision.allowed && !decision.requiresOwnerApproval) {
            "Website credential access was denied: ${decision.reason}"
        }

        val encoded = preferences.getString(
            storageKey(siteId),
            null
        ) ?: return null

        val packed = try {
            Base64.decode(encoded, Base64.NO_WRAP)
        } catch (_: IllegalArgumentException) {
            throw IllegalStateException(
                "Stored website credential data is damaged."
            )
        }

        if (packed.size <= IV_LENGTH + 16) {
            throw IllegalStateException(
                "Stored website credential data is incomplete."
            )
        }

        val key = getExistingSecretKey()
            ?: throw IllegalStateException(
                "The encryption key is unavailable. Credentials must be entered again."
            )

        val iv = packed.copyOfRange(0, IV_LENGTH)
        val encrypted = packed.copyOfRange(
            IV_LENGTH,
            packed.size
        )

        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            key,
            GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
        )

        val clearText = String(
            cipher.doFinal(encrypted),
            StandardCharsets.UTF_8
        )

        val root = JSONObject(clearText)
        val extrasObject = root.optJSONObject("extraFields")
            ?: JSONObject()

        val extras = mutableMapOf<String, String>()
        val keys = extrasObject.keys()

        while (keys.hasNext()) {
            val keyName = keys.next()
            extras[keyName] = extrasObject.optString(keyName)
        }

        return WebsiteCredentials(
            loginIdentifier = root.optString("loginIdentifier"),
            password = root.optString("password"),
            apiToken = root.optString("apiToken"),
            extraFields = extras
        )
    }

    @Synchronized
    fun hasCredentials(siteId: String): Boolean {
        validateSiteId(siteId)
        return preferences.contains(storageKey(siteId))
    }

    @Synchronized
    fun delete(siteId: String): Boolean {
        validateSiteId(siteId)

        return preferences.edit()
            .remove(storageKey(siteId))
            .commit()
    }

    @Synchronized
    fun clearAll() {
        check(preferences.edit().clear().commit()) {
            "Could not clear website credentials."
        }

        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)

        if (keyStore.containsAlias(KEY_ALIAS)) {
            keyStore.deleteEntry(KEY_ALIAS)
        }
    }

    private fun validateSiteId(siteId: String) {
        require(
            siteId.isNotBlank() &&
                siteId.length <= 100 &&
                siteId.matches(Regex("[A-Za-z0-9._-]+"))
        ) {
            "Website ID is invalid."
        }
    }

    private fun storageKey(siteId: String): String =
        CREDENTIAL_PREFIX + siteId

    private fun getExistingSecretKey(): SecretKey? {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)

        return keyStore.getKey(KEY_ALIAS, null) as? SecretKey
    }

    private fun getOrCreateSecretKey(): SecretKey {
        getExistingSecretKey()?.let { return it }

        val generator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            ANDROID_KEYSTORE
        )

        val specification = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or
                KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(
                KeyProperties.ENCRYPTION_PADDING_NONE
            )
            .setRandomizedEncryptionRequired(true)
            .setKeySize(256)
            .build()

        generator.init(specification)
        return generator.generateKey()
    }

    companion object {
        private const val PREFERENCES_NAME =
            "agent_website_credentials"

        private const val CREDENTIAL_PREFIX =
            "credential_"

        private const val KEY_ALIAS =
            "agent_simulation_website_vault"

        private const val ANDROID_KEYSTORE =
            "AndroidKeyStore"

        private const val TRANSFORMATION =
            "AES/GCM/NoPadding"

        private const val IV_LENGTH = 12
        private const val GCM_TAG_LENGTH_BITS = 128
        private const val MAX_FIELD_LENGTH = 4096
    }
}
