"""
AI Providers — Connecteurs pour les APIs IA (Mistral, Gemini, DeepSeek, GPT, Claude).
Utilise uniquement urllib (stdlib Python 3) au lieu de requests.
"""

import json
import os
import urllib.request
import urllib.error
import ssl
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Classe abstraite pour les providers IA."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.timeout = 60

    @abstractmethod
    def send_message(self, messages: list, model: str = None) -> str:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        pass

    @abstractmethod
    def get_available_models(self) -> list:
        pass


class AIProviderError(Exception):
    """Exception levée en cas d'erreur avec un provider IA."""

    def __init__(self, provider: str, message: str, status_code: int = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


def _get_ssl_context() -> ssl.SSLContext:
    """Crée un contexte SSL.
    
    Sur Windows, le default context fonctionne généralement bien.
    On ajoute un fallback au cas où.
    """
    global _ssl_context_cache
    if _ssl_context_cache is not None:
        return _ssl_context_cache

    ctx = ssl.create_default_context()
    try:
        # Test rapide de connexion SSL
        import urllib.request
        test_req = urllib.request.Request("https://api.mistral.ai", method="HEAD")
        urllib.request.urlopen(test_req, timeout=5, context=ctx)
        _ssl_context_cache = ctx
        return ctx
    except Exception:
        pass

    # Stratégie de fallback sans vérification SSL (dernier recours)
    ctx3 = ssl.create_default_context()
    ctx3.check_hostname = False
    ctx3.verify_mode = ssl.CERT_NONE
    _ssl_context_cache = ctx3
    return ctx3


# Cache du contexte SSL pour éviter de re-tester à chaque requête
_ssl_context_cache = None


def _post_json(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict:
    """Effectue une requête POST JSON avec urllib."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    for key, value in headers.items():
        req.add_header(key, value)

    ctx = _get_ssl_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        raise _HttpError(e.code, error_body)
    except urllib.error.URLError as e:
        if "timed out" in str(e.reason).lower() or "timeout" in str(e.reason).lower():
            raise TimeoutError(str(e.reason))
        raise ConnectionError(str(e.reason))
    except Exception as e:
        if "timed out" in str(e).lower():
            raise TimeoutError(str(e))
        raise


class _HttpError(Exception):
    def __init__(self, code, body=""):
        self.code = code
        self.body = body
        super().__init__(f"HTTP {code}: {body}")


class MistralProvider(AIProvider):
    """Provider pour l'API Mistral AI."""

    API_URL = "https://api.mistral.ai/v1/chat/completions"

    def get_name(self) -> str:
        return "Mistral"

    def get_default_model(self) -> str:
        return "mistral-small-latest"

    def get_available_models(self) -> list:
        return [
            "mistral-small-latest",
            "mistral-large-latest",
            "mistral-medium-latest",
            "open-mistral-nemo",
        ]

    def send_message(self, messages: list, model: str = None) -> str:
        model = model or self.get_default_model()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages}
        try:
            data = _post_json(self.API_URL, headers, payload, self.timeout)
            return data["choices"][0]["message"]["content"]
        except _HttpError as e:
            if e.code == 401:
                raise AIProviderError("Mistral", "Clé API invalide.", 401)
            if e.code == 429:
                raise AIProviderError("Mistral", "Quota dépassé. Réessaie plus tard.", 429)
            raise AIProviderError("Mistral", f"Erreur serveur (HTTP {e.code}).", e.code)
        except TimeoutError:
            raise AIProviderError("Mistral", "Timeout — le serveur met trop de temps à répondre.")
        except ConnectionError:
            raise AIProviderError("Mistral", "Impossible de se connecter au serveur.")
        except (KeyError, IndexError):
            raise AIProviderError("Mistral", "Réponse inattendue du serveur.")


class GeminiProvider(AIProvider):
    """Provider pour l'API Google Gemini."""

    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def get_name(self) -> str:
        return "Gemini"

    def get_default_model(self) -> str:
        return "gemini-2.0-flash"

    def get_available_models(self) -> list:
        return [
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]

    def send_message(self, messages: list, model: str = None) -> str:
        model = model or self.get_default_model()
        url = f"{self.API_BASE}/{model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        system_instruction = None
        gemini_contents = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                system_instruction = msg["content"]
                continue
            gemini_role = "user" if role == "user" else "model"
            gemini_contents.append({
                "role": gemini_role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {"contents": gemini_contents}
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        try:
            data = _post_json(url, headers, payload, self.timeout)
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except _HttpError as e:
            if e.code == 400:
                raise AIProviderError("Gemini", "Clé API invalide ou requête malformée.", 400)
            if e.code == 429:
                raise AIProviderError("Gemini", "Quota dépassé. Réessaie plus tard.", 429)
            raise AIProviderError("Gemini", f"Erreur serveur (HTTP {e.code}).", e.code)
        except TimeoutError:
            raise AIProviderError("Gemini", "Timeout — le serveur met trop de temps à répondre.")
        except ConnectionError:
            raise AIProviderError("Gemini", "Impossible de se connecter au serveur.")
        except (KeyError, IndexError):
            raise AIProviderError("Gemini", "Réponse inattendue du serveur.")


class DeepSeekProvider(AIProvider):
    """Provider pour l'API DeepSeek."""

    API_URL = "https://api.deepseek.com/v1/chat/completions"

    def get_name(self) -> str:
        return "DeepSeek"

    def get_default_model(self) -> str:
        return "deepseek-chat"

    def get_available_models(self) -> list:
        return ["deepseek-chat", "deepseek-reasoner"]

    def send_message(self, messages: list, model: str = None) -> str:
        model = model or self.get_default_model()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages}
        try:
            data = _post_json(self.API_URL, headers, payload, self.timeout)
            return data["choices"][0]["message"]["content"]
        except _HttpError as e:
            if e.code == 401:
                raise AIProviderError("DeepSeek", "Clé API invalide.", 401)
            if e.code == 429:
                raise AIProviderError("DeepSeek", "Quota dépassé. Réessaie plus tard.", 429)
            raise AIProviderError("DeepSeek", f"Erreur serveur (HTTP {e.code}).", e.code)
        except TimeoutError:
            raise AIProviderError("DeepSeek", "Timeout — le serveur met trop de temps à répondre.")
        except ConnectionError:
            raise AIProviderError("DeepSeek", "Impossible de se connecter au serveur.")
        except (KeyError, IndexError):
            raise AIProviderError("DeepSeek", "Réponse inattendue du serveur.")


class OpenAIProvider(AIProvider):
    """Provider pour l'API OpenAI (GPT)."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def get_name(self) -> str:
        return "GPT"

    def get_default_model(self) -> str:
        return "gpt-4o"

    def get_available_models(self) -> list:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

    def send_message(self, messages: list, model: str = None) -> str:
        model = model or self.get_default_model()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages}
        try:
            data = _post_json(self.API_URL, headers, payload, self.timeout)
            return data["choices"][0]["message"]["content"]
        except _HttpError as e:
            if e.code == 401:
                raise AIProviderError("GPT", "Clé API invalide.", 401)
            if e.code == 429:
                raise AIProviderError("GPT", "Quota dépassé. Réessaie plus tard.", 429)
            raise AIProviderError("GPT", f"Erreur serveur (HTTP {e.code}).", e.code)
        except TimeoutError:
            raise AIProviderError("GPT", "Timeout — le serveur met trop de temps à répondre.")
        except ConnectionError:
            raise AIProviderError("GPT", "Impossible de se connecter au serveur.")
        except (KeyError, IndexError):
            raise AIProviderError("GPT", "Réponse inattendue du serveur.")


class ClaudeProvider(AIProvider):
    """Provider pour l'API Anthropic Claude."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def get_name(self) -> str:
        return "Claude"

    def get_default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    def get_available_models(self) -> list:
        return [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ]

    def send_message(self, messages: list, model: str = None) -> str:
        model = model or self.get_default_model()
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        system_text = None
        api_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_text = msg["content"]
            else:
                api_messages.append(msg)

        payload = {
            "model": model,
            "max_tokens": 4096,
            "messages": api_messages,
        }
        if system_text:
            payload["system"] = system_text

        try:
            data = _post_json(self.API_URL, headers, payload, self.timeout)
            content_blocks = data.get("content", [])
            text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
            return "\n".join(text_parts)
        except _HttpError as e:
            if e.code == 401:
                raise AIProviderError("Claude", "Clé API invalide.", 401)
            if e.code == 429:
                raise AIProviderError("Claude", "Quota dépassé. Réessaie plus tard.", 429)
            raise AIProviderError("Claude", f"Erreur serveur (HTTP {e.code}).", e.code)
        except TimeoutError:
            raise AIProviderError("Claude", "Timeout — le serveur met trop de temps à répondre.")
        except ConnectionError:
            raise AIProviderError("Claude", "Impossible de se connecter au serveur.")
        except (KeyError, IndexError):
            raise AIProviderError("Claude", "Réponse inattendue du serveur.")


# Registry of all available providers
PROVIDERS = {
    "Mistral": MistralProvider,
    "Gemini": GeminiProvider,
    "DeepSeek": DeepSeekProvider,
    "GPT": OpenAIProvider,
    "Claude": ClaudeProvider,
}


def get_provider(name: str, api_key: str) -> AIProvider:
    """Crée et retourne une instance du provider spécifié."""
    if name not in PROVIDERS:
        raise ValueError(f"Provider '{name}' inconnu. Disponibles: {list(PROVIDERS.keys())}")
    return PROVIDERS[name](api_key)
