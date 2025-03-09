#!/usr/bin/env python3
import os
import subprocess

def test_github_sync_setup():
    # Prüfe, ob Git konfiguriert ist
    try:
        result = subprocess.run(
            ["git", "config", "--get", "user.name"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        assert result.stdout.strip(), "Git-Benutzername nicht konfiguriert"
        
        result = subprocess.run(
            ["git", "config", "--get", "user.email"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        assert result.stdout.strip(), "Git-E-Mail nicht konfiguriert"
        
        # Prüfe, ob das Repository gültig ist
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        assert result.stdout.strip() == "true", "Kein gültiges Git-Repository"
        
        print("GitHub-Sync-Setup erfolgreich getestet")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Testen des GitHub-Sync-Setups: {e}")
        return False

if __name__ == "__main__":
    test_github_sync_setup() 