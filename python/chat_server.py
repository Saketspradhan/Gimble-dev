#!/usr/bin/env python3
import argparse
import os
import platform
import threading
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from flask import Flask, jsonify, request, send_from_directory
except ModuleNotFoundError as exc:
    missing = str(exc).split("'")[-2] if "'" in str(exc) else "flask"
    req_file = Path(__file__).resolve().parent / "requirements.txt"
    print(f"Missing Python package: {missing}")
    print("Install dependencies with:")
    print(f"  python3 -m pip install -r {req_file}")
    raise SystemExit(1)


DEFAULT_SYSTEM_PROMPT = "You are Gimble Assistant. Be concise, practical, and clear."
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
REQ_FILE = Path(__file__).resolve().parent / "requirements.txt"
DEFAULT_GPTQ4K_LABEL = "GPT-Q 4K (Local CPU)"
DEFAULT_LLAMA_LABEL = "LLaMA 3 7B (Local CPU)"
DEFAULT_OPENAI_LABEL = "GPT-4 (OpenAI API)"


# Default GPT-Q 4K path required by the product requirement.
# We use a quantized GGUF artifact and store it with this canonical filename.
DEFAULT_GPTQ4K_FILE = "gptq-4k-quantized.gguf"
DEFAULT_GPTQ4K_URL = (
    "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/"
    "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
)


def chat_env_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "gimble" / "chat.env"
    if platform.system().lower() == "darwin":
        return Path.home() / "Library" / "Application Support" / "gimble" / "chat.env"
    return Path.home() / ".config" / "gimble" / "chat.env"


def load_chat_env() -> Dict[str, str]:
    path = chat_env_path()
    if not path.exists():
        return {}
    values: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def is_apple_silicon() -> bool:
    return platform.system().lower() == "darwin" and platform.machine().lower() in {"arm64", "aarch64"}


def resolve_default_model() -> str:
    explicit = os.getenv("GIMBLE_DEFAULT_MODEL", "").strip().lower()
    if explicit in {"gptq4k", "llama", "gpt4"}:
        return explicit
    if is_apple_silicon():
        return "gptq4k"
    return "llama"


def split_system_prefix(text: str) -> Tuple[str, str]:
    stripped = text.strip()
    if not stripped.lower().startswith("system:"):
        return "", text

    first_line, _, tail = stripped.partition("\n")
    system_prompt = first_line[len("System:") :].strip()
    user_text = tail.strip()
    if user_text.lower().startswith("user:"):
        user_text = user_text[len("User:") :].strip()
    return system_prompt, user_text


class ConversationStore:
    def __init__(self, model_keys: List[str]) -> None:
        self._lock = threading.Lock()
        self._messages: Dict[str, List[Dict[str, str]]] = {
            key: [{"role": "system", "content": DEFAULT_SYSTEM_PROMPT}] for key in model_keys
        }

    def set_system_prompt(self, model_key: str, prompt: str) -> None:
        prompt = prompt.strip()
        if not prompt:
            return
        with self._lock:
            current = self._messages[model_key]
            remainder = [m for m in current[1:] if m.get("role") != "system"]
            self._messages[model_key] = [{"role": "system", "content": prompt}] + remainder
            self._trim(model_key)

    def append_user(self, model_key: str, text: str) -> List[Dict[str, str]]:
        with self._lock:
            self._messages[model_key].append({"role": "user", "content": text})
            self._trim(model_key)
            return list(self._messages[model_key])

    def append_assistant(self, model_key: str, text: str) -> None:
        with self._lock:
            self._messages[model_key].append({"role": "assistant", "content": text})
            self._trim(model_key)

    def _trim(self, model_key: str) -> None:
        msgs = self._messages[model_key]
        if len(msgs) > 31:
            self._messages[model_key] = [msgs[0]] + msgs[-30:]


class LlamaCppBackend:
    def __init__(
        self,
        *,
        label: str,
        model_path: Path,
        auto_download: bool,
        hf_repo: str,
        hf_file: str,
        direct_url: str,
        n_ctx: int,
        n_threads: int,
    ) -> None:
        self.label = label
        self.model_path = model_path
        self.auto_download = auto_download
        self.hf_repo = hf_repo
        self.hf_file = hf_file
        self.direct_url = direct_url
        self.n_ctx = n_ctx
        self.n_threads = n_threads

        self._lock = threading.Lock()
        self._llm = None

    def available(self) -> bool:
        return self.model_path.exists() or self.auto_download

    def _download_via_hf(self) -> bool:
        if not self.hf_repo or not self.hf_file:
            return False
        try:
            from huggingface_hub import hf_hub_download
        except ModuleNotFoundError:
            raise RuntimeError(f"huggingface-hub is required. Run: python3 -m pip install -r {REQ_FILE}")

        downloaded = hf_hub_download(
            repo_id=self.hf_repo,
            filename=self.hf_file,
            local_dir=str(self.model_path.parent),
            local_dir_use_symlinks=False,
        )
        downloaded_path = Path(downloaded)
        if downloaded_path != self.model_path:
            downloaded_path.replace(self.model_path)
        return True

    def _download_via_url(self) -> bool:
        if not self.direct_url:
            return False
        with urllib.request.urlopen(self.direct_url) as src, self.model_path.open("wb") as dst:
            dst.write(src.read())
        return True

    def _ensure_model_file(self) -> None:
        if self.model_path.exists():
            return
        if not self.auto_download:
            raise RuntimeError(f"Model missing at {self.model_path}")

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading model for {self.label} ...")
        try:
            if self._download_via_hf():
                return
        except Exception as exc:  # noqa: BLE001
            print(f"HF download failed for {self.label}: {exc}")
        if self._download_via_url():
            return

        raise RuntimeError(
            f"Could not download {self.label}. Set model path directly with env var or configure download source."
        )

    def _ensure_loaded(self):
        with self._lock:
            if self._llm is not None:
                return self._llm

            self._ensure_model_file()
            try:
                from llama_cpp import Llama
            except ModuleNotFoundError:
                raise RuntimeError(f"llama-cpp-python is required. Run: python3 -m pip install -r {REQ_FILE}")

            print(f"Loading {self.label} from {self.model_path} ...")
            self._llm = Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                n_gpu_layers=0,
                verbose=False,
            )
            return self._llm

    def chat(self, messages: List[Dict[str, str]]) -> str:
        llm = self._ensure_loaded()
        try:
            result = llm.create_chat_completion(
                messages=messages,
                max_tokens=512,
                temperature=0.7,
            )
            return (result["choices"][0]["message"]["content"] or "").strip() or "(empty response)"
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"{self.label} inference error: {exc}")


class OpenAIBackend:
    def __init__(self) -> None:
        env = load_chat_env()
        self.api_key = os.getenv("OPENAI_API_KEY", env.get("OPENAI_API_KEY", "")).strip()
        self.model = os.getenv("OPENAI_MODEL", env.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)).strip() or DEFAULT_OPENAI_MODEL
        self.label = DEFAULT_OPENAI_LABEL

    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured. Set it in env or gimble chat.env")
        try:
            from openai import OpenAI
        except ModuleNotFoundError:
            raise RuntimeError(f"openai package is required. Run: python3 -m pip install -r {REQ_FILE}")

        client = OpenAI(api_key=self.api_key)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )
            text = response.choices[0].message.content or ""
            return text.strip() or "(empty response)"
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"OpenAI API error: {exc}")


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(Path(__file__).resolve().parent / "web"), static_url_path="")

    cache_dir = Path(os.getenv("GIMBLE_MODEL_CACHE_DIR", Path.home() / ".cache" / "gimble" / "models"))
    n_ctx = int(os.getenv("GIMBLE_LLAMA_N_CTX", "2048"))
    n_threads = int(os.getenv("GIMBLE_LLAMA_THREADS", str(max((os.cpu_count() or 2) - 1, 1))))

    gptq4k = LlamaCppBackend(
        label=DEFAULT_GPTQ4K_LABEL,
        model_path=Path(os.getenv("GIMBLE_GPTQ4K_MODEL_PATH", cache_dir / DEFAULT_GPTQ4K_FILE)),
        auto_download=os.getenv("GIMBLE_GPTQ4K_AUTO_DOWNLOAD", "1") == "1",
        hf_repo=os.getenv("GIMBLE_GPTQ4K_HF_REPO", ""),
        hf_file=os.getenv("GIMBLE_GPTQ4K_HF_FILE", ""),
        direct_url=os.getenv("GIMBLE_GPTQ4K_URL", DEFAULT_GPTQ4K_URL),
        n_ctx=n_ctx,
        n_threads=n_threads,
    )

    llama = LlamaCppBackend(
        label=DEFAULT_LLAMA_LABEL,
        model_path=Path(os.getenv("GIMBLE_LLAMA_MODEL_PATH", cache_dir / "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf")),
        auto_download=os.getenv("GIMBLE_LLAMA_AUTO_DOWNLOAD", "1") == "1",
        hf_repo=os.getenv("GIMBLE_LLAMA_HF_REPO", "bartowski/Meta-Llama-3-8B-Instruct-GGUF"),
        hf_file=os.getenv("GIMBLE_LLAMA_HF_FILE", "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"),
        direct_url=os.getenv("GIMBLE_LLAMA_URL", ""),
        n_ctx=n_ctx,
        n_threads=n_threads,
    )

    gpt4 = OpenAIBackend()

    model_registry = {
        "gptq4k": gptq4k,
        "llama": llama,
        "gpt4": gpt4,
    }
    default_model = resolve_default_model()
    if not model_registry[default_model].available():
        default_model = "llama" if model_registry["llama"].available() else "gpt4"

    store = ConversationStore(list(model_registry.keys()))

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/models")
    def models():
        return jsonify(
            {
                "default": default_model,
                "models": [
                    {"key": "gptq4k", "label": gptq4k.label, "available": gptq4k.available()},
                    {"key": "llama", "label": llama.label, "available": llama.available()},
                    {"key": "gpt4", "label": gpt4.label, "available": gpt4.available()},
                ],
            }
        )

    @app.post("/api/chat")
    def chat():
        payload = request.get_json(silent=True) or {}
        raw_text = (payload.get("message") or "").strip()
        model_key = (payload.get("model") or default_model).strip()
        explicit_system = (payload.get("system_prompt") or "").strip()

        if model_key not in model_registry:
            return jsonify({"error": f"unknown model: {model_key}"}), 400

        prefixed_system, user_text = split_system_prefix(raw_text)
        system_prompt = explicit_system or prefixed_system
        if system_prompt:
            store.set_system_prompt(model_key, system_prompt)

        user_text = user_text.strip()
        if not user_text:
            if system_prompt:
                return jsonify({"reply": "System prompt updated for this model session."})
            return jsonify({"error": "message cannot be empty"}), 400

        history = store.append_user(model_key, user_text)
        backend = model_registry[model_key]
        try:
            reply = backend.chat(history)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": str(exc)}), 502

        store.append_assistant(model_key, reply)
        return jsonify({"reply": reply})

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Gimble Python chat server")
    parser.add_argument("--port", type=int, default=5555)
    args = parser.parse_args()

    app = create_app()
    print(f"Python chat server listening on http://127.0.0.1:{args.port}")
    app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
