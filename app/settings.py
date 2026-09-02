"""
Settings — Gestion des paramètres de l'application (clés API, thème, préférences).
Les paramètres sont stockés dans un fichier config.json.
"""

import json
import os
import base64
from pathlib import Path


class Settings:
    """Gère la configuration persistante de l'application."""

    def __init__(self, app_dir: str):
        self.app_dir = Path(app_dir)
        self.config_path = self.app_dir / "config.json"
        self._defaults = {
            "api_keys": {
                "Mistral": "",
                "Gemini": "",
                "DeepSeek": "",
                "GPT": "",
                "Claude": "",
            },
            "default_provider": "",
            "theme": "dark",
            "language": "fr",
            "auto_save_interval": 30,
            "editor_font_size": 14,
            "models": {
                "Mistral": "mistral-small-latest",
                "Gemini": "gemini-2.0-flash",
                "DeepSeek": "deepseek-chat",
                "GPT": "gpt-4o",
                "Claude": "claude-sonnet-4-20250514",
            },
            "recent_files": [],
            "last_opened_file": "",
        }
        self._config = {}
        self.load()

    def load(self):
        """Charge les paramètres depuis le fichier config.json."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                # Decode API keys
                if "api_keys" in self._config:
                    for provider, key in self._config["api_keys"].items():
                        if key:
                            try:
                                self._config["api_keys"][provider] = base64.b64decode(
                                    key.encode()
                                ).decode()
                            except Exception:
                                pass
            except (json.JSONDecodeError, IOError):
                self._config = {}

        # Merge with defaults
        for key, default_value in self._defaults.items():
            if key not in self._config:
                self._config[key] = default_value
            elif isinstance(default_value, dict):
                for sub_key, sub_default in default_value.items():
                    if sub_key not in self._config[key]:
                        self._config[key][sub_key] = sub_default

        # Override API keys from api_keys.txt
        api_keys_path = self.app_dir / "api_keys.txt"
        if api_keys_path.exists():
            try:
                with open(api_keys_path, "r", encoding="utf-8") as f:
                    if "api_keys" not in self._config:
                        self._config["api_keys"] = {}
                    for line in f:
                        line = line.strip()
                        if line and "=" in line and not line.startswith("#"):
                            provider, key = line.split("=", 1)
                            self._config["api_keys"][provider.strip()] = key.strip()
            except IOError:
                pass
        else:
            # Create template api_keys.txt
            try:
                os.makedirs(self.app_dir, exist_ok=True)
                with open(api_keys_path, "w", encoding="utf-8") as f:
                    f.write("# Fichier de configuration des cles API\n")
                    f.write("# Renseignez vos cles API ci-dessous apres le signe '='\n\n")
                    for p in self._defaults["api_keys"].keys():
                        f.write(f"{p}=\n")
            except IOError:
                pass

    def save(self):
        """Sauvegarde les paramètres dans config.json."""
        config_to_save = json.loads(json.dumps(self._config))

        # Encode API keys
        if "api_keys" in config_to_save:
            for provider, key in config_to_save["api_keys"].items():
                if key:
                    config_to_save["api_keys"][provider] = base64.b64encode(
                        key.encode()
                    ).decode()

        os.makedirs(self.app_dir, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, indent=2, ensure_ascii=False)

    def get_api_key(self, provider: str) -> str:
        return self._config.get("api_keys", {}).get(provider, "")

    def set_api_key(self, provider: str, key: str):
        if "api_keys" not in self._config:
            self._config["api_keys"] = {}
        self._config["api_keys"][provider] = key

    def get_default_provider(self) -> str:
        return self._config.get("default_provider", "")

    def set_default_provider(self, provider: str):
        self._config["default_provider"] = provider

    def get_theme(self) -> str:
        return self._config.get("theme", "dark")

    def set_theme(self, theme: str):
        self._config["theme"] = theme

    def get_model(self, provider: str) -> str:
        return self._config.get("models", {}).get(provider, "")

    def set_model(self, provider: str, model: str):
        if "models" not in self._config:
            self._config["models"] = {}
        self._config["models"][provider] = model

    def get_auto_save_interval(self) -> int:
        return self._config.get("auto_save_interval", 30)

    def get_editor_font_size(self) -> int:
        return self._config.get("editor_font_size", 14)

    def set_editor_font_size(self, size: int):
        self._config["editor_font_size"] = size

    def get_configured_providers(self) -> list:
        return [
            provider
            for provider, key in self._config.get("api_keys", {}).items()
            if key.strip()
        ]

    def get_recent_files(self) -> list:
        """Retourne la liste des fichiers récents (max 5)."""
        return self._config.get("recent_files", [])[:5]

    def add_recent_file(self, filepath: str):
        """Ajoute un fichier à la liste des récents."""
        recent = self._config.get("recent_files", [])
        # Remove if already present
        recent = [f for f in recent if f != filepath]
        # Add at beginning
        recent.insert(0, filepath)
        # Keep max 5
        self._config["recent_files"] = recent[:5]
        self.save()
        
    def get_last_opened_file(self) -> str:
        return self._config.get("last_opened_file", "")
        
    def set_last_opened_file(self, filepath: str):
        self._config["last_opened_file"] = filepath
        self.save()
