FROM ghcr.io/ggml-org/llama.cpp:server

WORKDIR /models

RUN curl -L \
    --fail \
    --retry 5 \
    --retry-delay 5 \
    -o /models/Qwen3-0.6B-Q4_K_M.gguf \
    https://huggingface.co/tensorblock/Qwen_Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q4_K_M.gguf

EXPOSE 8080

CMD [
    "/app/llama-server",
    "-m",
    "/models/Qwen3-0.6B-Q4_K_M.gguf",
    "--host",
    "0.0.0.0",
    "--port",
    "8080",
    "-c",
    "2048",
    "--parallel",
    "1",
    "--alias",
    "qwen3-0.6b"
]