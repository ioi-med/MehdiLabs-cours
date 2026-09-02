# MehdiLabs Cours (Version Windows)

Une application complète de gestion de cours avec un éditeur Markdown, une preview et un assistant IA intégré, conçue spécialement pour fonctionner sur Windows sans aucune dépendance externe.

## 🚀 Installation & Lancement

**Aucune installation complexe n'est requise.**
Le programme utilise uniquement les bibliothèques standard de Python 3.

1. Assurez-vous d'avoir **Python 3** installé sur votre PC (téléchargeable sur [python.org](https://www.python.org/downloads/)).
   > ⚠️ **IMPORTANT** : Lors de l'installation de Python, cochez la case **"Add Python to PATH"** !
2. Double-cliquez sur le fichier `run_windows.bat` pour lancer l'application.

Alternative via l'Invite de commandes (cmd) ou PowerShell :
```cmd
cd chemin\vers\MehdiLabs-Cours-Windows
python main.py
```

## ⚙️ Configuration des clés API

L'assistant IA nécessite des clés API pour fonctionner. Vous pouvez les configurer de deux manières :
1. Via l'interface graphique : Onglet **Paramètres** > **Ouvrir api_keys.txt**.
2. Manuellement : Modifiez le fichier `api_keys.txt` à la racine du projet.

## 🛠️ Composants (100% natifs)

- **GUI** : Construit avec `tkinter` (inclus dans Python 3).
- **Requêtes HTTP** : Utilise `urllib` (inclus dans Python 3).
- **Markdown** : Parseur personnalisé léger ne nécessitant pas de bibliothèques externes.

## 🔄 Différences avec la version macOS

- Raccourcis clavier : `Ctrl` au lieu de `Cmd`
- Polices : Segoe UI / Consolas (polices système Windows)
- Synthèse vocale : Utilise Windows SAPI (au lieu de `say` sur macOS)
- Notifications : Utilise les notifications Windows natives
