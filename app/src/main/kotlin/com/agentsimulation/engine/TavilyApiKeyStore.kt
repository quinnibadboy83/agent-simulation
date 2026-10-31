
package com.agentsimulation.engine

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Stores the Tavily API key encrypted with an Android Keystore key.
 *
 * The API key is never stored as plain text in SharedPreferences.
 * The encryption key is held by Android Keystore.
 */
class TavilyApiKeyStore(context: Context) {

    private val preferences = context.applicationContext
        .getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    @Synchronized
    fun save(apiKey: String) {
        val cleanKey = apiKey.trim()

        require(cleanKey.isNotEmpty()) {
            "Tavily API key cannot be empty."
        }

        require(cleanKey.length <= 512) {
            "Tavily API key is unexpectedly long."
        }

        val cipher = Cipher.getInstance(TRANSFORMATION)

        cipher.init(
            Cipher.ENCRYPT_MODE,
            getOrCreateSecretKey()
        )

        val encryptedBytes = cipher.doFinal(
            cleanKey.toByteArray(StandardCharsets.UTF_8)
        )

        val packedBytes = cipher.iv + encryptedBytes

        val encoded = Base64.encodeToString(
            packedBytes,
            Base64.NO_WRAP
        )

        check(
            preferences.edit()
                .putString(KEY_ENCRYPTED_API_KEY, encoded)
                .commit()
        ) {
            "Could not securely save the Tavily API key."
        }
    }

    @Synchronized
    fun get(): String? {
        val encoded = preferences.getString(
            KEY_ENCRYPTED_API_KEY,
            null
        ) ?: return null

        val key = getExistingSecretKey()
            ?: throw IllegalStateException(
                "The saved API key cannot be decrypted. Please enter it again."
            )

        val packedBytes = try {
            Base64.decode(encoded, Base64.NO_WRAP)
        } catch (_: IllegalArgumentException) {
            throw IllegalStateException(
                "The saved API key data is damaged. Please enter it again."
            )
        }

        if (packedBytes.size <= IV_LENGTH + 16) {
            throw IllegalStateException(
                "The saved API key data is incomplete. Please enter it again."
            )
        }

        val iv = packedBytes.copyOfRange(0, IV_LENGTH)
        val encryptedBytes = packedBytes.copyOfRange(
            IV_LENGTH,
            packedBytes.size
        )

        val cipher = Cipher.getInstance(TRANSFORMATION)

        cipher.init(
            Cipher.DECRYPT_MODE,
            key,
            GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
        )

        return String(
            cipher.doFinal(encryptedBytes),
            StandardCharsets.UTF_8
        )
    }

    @Synchronized
    fun hasKey(): Boolean {
        return preferences.contains(KEY_ENCRYPTED_API_KEY)
    }

    @Synchronized
    fun clear() {
        preferences.edit()
            .remove(KEY_ENCRYPTED_API_KEY)
            .commit()

        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)

        if (keyStore.containsAlias(KEY_ALIAS)) {
            keyStore.deleteEntry(KEY_ALIAS)
        }
    }

    private fun getExistingSecretKey(): SecretKey? {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE)
        keyStore.load(null)

        return keyStore.getKey(
            KEY_ALIAS,
            null
        ) as? SecretKey
    }

    private fun getOrCreateSecretKey(): SecretKey {
        getExistingSecretKey()?.let {
            return it
        }

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
            "agent_research_security"

        private const val KEY_ENCRYPTED_API_KEY =
            "encrypted_tavily_api_key"

        private const val KEY_ALIAS =
            "agent_simulation_tavily_key"

        private const val ANDROID_KEYSTORE =
            "AndroidKeyStore"

        private const val TRANSFORMATION =
            "AES/GCM/NoPadding"

        private const val IV_LENGTH = 12

        private const val GCM_TAG_LENGTH_BITS = 128
    }
}
