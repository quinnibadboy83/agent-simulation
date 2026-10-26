
#include <jni.h>
#include <llama.h>

#include <algorithm>
#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

namespace {

std::mutex engine_mutex;
llama_model* engine_model = nullptr;
llama_context* engine_context = nullptr;
bool backend_initialized = false;

void release_model() {
    if (engine_context != nullptr) {
        llama_free(engine_context);
        engine_context = nullptr;
    }

    if (engine_model != nullptr) {
        llama_model_free(engine_model);
        engine_model = nullptr;
    }
}

std::string load_model(const std::string& path) {
    std::lock_guard<std::mutex> lock(engine_mutex);

    if (path.empty()) {
        return "ERROR: Model path is empty.";
    }

    release_model();

    if (!backend_initialized) {
        llama_backend_init();
        backend_initialized = true;
    }

    llama_model_params model_params =
        llama_model_default_params();
    model_params.n_gpu_layers = 0;

    engine_model = llama_model_load_from_file(
        path.c_str(),
        model_params
    );

    if (engine_model == nullptr) {
        return "ERROR: Could not load GGUF model.";
    }

    llama_context_params context_params =
        llama_context_default_params();

    context_params.n_ctx = 2048;
    context_params.n_batch = 512;
    context_params.n_threads = 4;
    context_params.n_threads_batch = 4;

    engine_context = llama_init_from_model(
        engine_model,
        context_params
    );

    if (engine_context == nullptr) {
        release_model();
        return "ERROR: Could not create inference context.";
    }

    return "READY: GGUF model loaded for CPU inference.";
}

std::string generate_text(const std::string& user_prompt) {
    std::lock_guard<std::mutex> lock(engine_mutex);

    if (engine_model == nullptr || engine_context == nullptr) {
        return "ERROR: Load a GGUF model first.";
    }

    if (user_prompt.empty()) {
        return "ERROR: Prompt is empty.";
    }

    const llama_vocab* vocab =
        llama_model_get_vocab(engine_model);

    if (vocab == nullptr) {
        return "ERROR: Model vocabulary is unavailable.";
    }

    const std::string formatted_prompt =
        "<|im_start|>user\n" +
        user_prompt +
        "<|im_end|>\n<|im_start|>assistant\n";

    llama_memory_clear(
        llama_get_memory(engine_context),
        true
    );

    size_t token_capacity =
        std::max<size_t>(
            formatted_prompt.size() * 2 + 128,
            512
        );

    std::vector<llama_token> prompt_tokens(token_capacity);

    int32_t token_count = llama_tokenize(
        vocab,
        formatted_prompt.c_str(),
        static_cast<int32_t>(formatted_prompt.size()),
        prompt_tokens.data(),
        static_cast<int32_t>(prompt_tokens.size()),
        true,
        true
    );

    if (token_count < 0) {
        token_capacity = static_cast<size_t>(-token_count);
        prompt_tokens.resize(token_capacity);

        token_count = llama_tokenize(
            vocab,
            formatted_prompt.c_str(),
            static_cast<int32_t>(formatted_prompt.size()),
            prompt_tokens.data(),
            static_cast<int32_t>(prompt_tokens.size()),
            true,
            true
        );
    }

    if (token_count <= 0) {
        return "ERROR: Prompt tokenization failed (code " +
            std::to_string(token_count) + ").";
    }

    prompt_tokens.resize(static_cast<size_t>(token_count));

    const uint32_t context_size = llama_n_ctx(engine_context);

    if (prompt_tokens.size() >= context_size) {
        return "ERROR: Prompt exceeds the model context limit.";
    }

    llama_batch batch = llama_batch_get_one(
        prompt_tokens.data(),
        static_cast<int32_t>(prompt_tokens.size())
    );

    if (llama_decode(engine_context, batch) != 0) {
        return "ERROR: Prompt evaluation failed.";
    }

    llama_sampler* sampler = llama_sampler_chain_init(
        llama_sampler_chain_default_params()
    );

    if (sampler == nullptr) {
        return "ERROR: Could not create text sampler.";
    }

    llama_sampler_chain_add(
        sampler,
        llama_sampler_init_greedy()
    );

    std::string output;
    constexpr int max_generated_tokens = 128;

    for (int i = 0; i < max_generated_tokens; ++i) {
        llama_token token =
            llama_sampler_sample(sampler, engine_context, -1);

        if (llama_vocab_is_eog(vocab, token)) {
            break;
        }

        char piece[512];

        const int32_t piece_size = llama_token_to_piece(
            vocab,
            token,
            piece,
            static_cast<int32_t>(sizeof(piece)),
            0,
            true
        );

        if (piece_size > 0) {
            output.append(
                piece,
                static_cast<size_t>(piece_size)
            );
        } else if (piece_size < 0) {
            const size_t required =
                static_cast<size_t>(-piece_size);

            std::vector<char> larger_piece(required);

            const int32_t larger_size = llama_token_to_piece(
                vocab,
                token,
                larger_piece.data(),
                static_cast<int32_t>(larger_piece.size()),
                0,
                true
            );

            if (larger_size > 0) {
                output.append(
                    larger_piece.data(),
                    static_cast<size_t>(larger_size)
                );
            }
        }

        batch = llama_batch_get_one(&token, 1);

        if (llama_decode(engine_context, batch) != 0) {
            llama_sampler_free(sampler);
            return "ERROR: Text generation failed.";
        }
    }

    llama_sampler_free(sampler);

    if (output.empty()) {
        return "ERROR: Generation produced no text. The model may have stopped immediately.";
    }

    return output;
}

std::string from_java_string(JNIEnv* env, jstring value) {
    if (value == nullptr) {
        return {};
    }

    const char* chars = env->GetStringUTFChars(value, nullptr);

    if (chars == nullptr) {
        return {};
    }

    std::string result(chars);
    env->ReleaseStringUTFChars(value, chars);

    return result;
}

jstring to_java_string(JNIEnv* env, const std::string& value) {
    return env->NewStringUTF(value.c_str());
}

}  // namespace

extern "C"
JNIEXPORT jstring JNICALL
Java_com_agentsimulation_engine_NativeInferenceBridge_nativeGetEngineStatus(
    JNIEnv* env,
    jobject /* thiz */
) {
    std::lock_guard<std::mutex> lock(engine_mutex);

    if (engine_context != nullptr) {
        return to_java_string(
            env,
            "Native engine ready; model loaded."
        );
    }

    return to_java_string(
        env,
        "Native engine available; no model loaded."
    );
}

extern "C"
JNIEXPORT jstring JNICALL
Java_com_agentsimulation_engine_NativeInferenceBridge_nativeLoadModel(
    JNIEnv* env,
    jobject /* thiz */,
    jstring model_path
) {
    return to_java_string(
        env,
        load_model(from_java_string(env, model_path))
    );
}

extern "C"
JNIEXPORT jstring JNICALL
Java_com_agentsimulation_engine_NativeInferenceBridge_nativeGenerate(
    JNIEnv* env,
    jobject /* thiz */,
    jstring prompt
) {
    return to_java_string(
        env,
        generate_text(from_java_string(env, prompt))
    );
}

extern "C"
JNIEXPORT void JNICALL
Java_com_agentsimulation_engine_NativeInferenceBridge_nativeClose(
    JNIEnv* /* env */,
    jobject /* thiz */
) {
    std::lock_guard<std::mutex> lock(engine_mutex);
    release_model();
}
