# End-to-End Tests für den Bookmark Manager

Diese Dokumentation beschreibt die End-to-End (E2E) Tests für den Bookmark Manager, die mit Cypress implementiert wurden.

## Übersicht

Die E2E-Tests validieren den vollständigen Workflow des Bookmark Managers, von der Datei-Hochladung über die Verarbeitung bis zur Report-Generierung. Sie stellen sicher, dass alle Komponenten nahtlos zusammenarbeiten und die Benutzeroberfläche korrekt auf Benutzerinteraktionen reagiert.

## Teststruktur

Die Tests sind in drei Hauptkategorien unterteilt:

1. **Workflow-Tests**: Testen den vollständigen Benutzer-Workflow
2. **UI-Tests**: Testen das responsive Design und die UI-Komponenten
3. **Performance-Tests**: Testen das Verhalten unter Last und bei Netzwerkproblemen

### Workflow-Tests

Diese Tests validieren den Hauptanwendungsfall des Bookmark Managers:

- Hochladen einer Bookmark-Datei
- Verarbeitung der Bookmarks
- Generierung eines Reports
- Anzeige von Statistiken

### UI-Tests

Diese Tests überprüfen das responsive Design der Anwendung auf verschiedenen Geräten:

- Desktop
- Tablet
- Mobilgeräte

### Performance-Tests

Diese Tests überprüfen das Verhalten der Anwendung unter Last und bei Netzwerkproblemen:

- Verarbeitung großer Dateien
- UI-Reaktionsfähigkeit während der Verarbeitung
- Gleichzeitige Verarbeitungsanfragen
- Fehlerbehandlung bei Netzwerkproblemen

## Ausführung der Tests

### Lokal

Um die Tests lokal auszuführen, verwenden Sie das bereitgestellte Skript:

```bash
./run_e2e_tests.sh
```

Das Skript bietet zwei Modi:

1. **UI-Modus**: Öffnet Cypress im interaktiven Modus, wo Sie Tests einzeln ausführen und debuggen können.
2. **Headless-Modus**: Führt alle Tests automatisch aus und generiert Berichte.

### In der CI/CD-Pipeline

Die Tests werden automatisch in der GitHub Actions CI/CD-Pipeline ausgeführt. Die Ergebnisse (Screenshots und Videos) werden als Artefakte gespeichert und können nach dem Test-Lauf heruntergeladen werden.

## Testumgebung

Die Tests werden in einer Docker-basierten Umgebung ausgeführt, die alle erforderlichen Services enthält:

- Webapp (Frontend)
- Processor (Backend)
- Datenbank (PostgreSQL)
- Cache (Redis)

Diese Umgebung ist in der Datei `docker-compose.e2e.yml` definiert.

## Mocking

Die Tests verwenden Cypress-Interceptors, um API-Aufrufe zu mocken. Dies ermöglicht:

- Konsistente Testbedingungen
- Simulation von Fehlerfällen
- Kontrolle über Antwortzeiten
- Simulation von Statusupdates

## Erweiterung der Tests

### Hinzufügen eines neuen Tests

1. Erstellen Sie eine neue Testdatei in einem der Verzeichnisse:
   - `webapp/cypress/e2e/workflow/` für Workflow-Tests
   - `webapp/cypress/e2e/ui/` für UI-Tests
   - `webapp/cypress/e2e/performance/` für Performance-Tests

2. Verwenden Sie die Cypress-Syntax, um den Test zu definieren:

```javascript
describe('Mein neuer Test', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('sollte etwas tun', () => {
    // Test-Implementierung
  });
});
```

### Hinzufügen von benutzerdefinierten Befehlen

Benutzerdefinierte Befehle können in der Datei `webapp/cypress/support/commands.js` hinzugefügt werden:

```javascript
Cypress.Commands.add('meinBefehl', (param1, param2) => {
  // Implementierung
});
```

## Fehlerbehebung

### Häufige Probleme

1. **Tests schlagen fehl, weil Elemente nicht gefunden werden**:
   - Überprüfen Sie, ob die Selektoren korrekt sind
   - Fügen Sie `data-testid`-Attribute zu den Elementen hinzu
   - Verwenden Sie längere Timeouts für asynchrone Operationen

2. **Tests sind instabil**:
   - Vermeiden Sie Abhängigkeiten zwischen Tests
   - Verwenden Sie `beforeEach` für einen konsistenten Ausgangszustand
   - Verwenden Sie explizite Wartezeiten statt impliziter

3. **Netzwerkprobleme**:
   - Überprüfen Sie, ob die Docker-Container korrekt kommunizieren können
   - Überprüfen Sie, ob die Ports korrekt zugeordnet sind

## Best Practices

1. **Verwenden Sie `data-testid`-Attribute** für Selektoren, um unabhängig von CSS-Änderungen zu sein
2. **Testen Sie einen Anwendungsfall pro Test**, um die Fehlersuche zu erleichtern
3. **Verwenden Sie aussagekräftige Beschreibungen** für Tests und Assertions
4. **Vermeiden Sie Abhängigkeiten zwischen Tests**, um isolierte Fehler zu ermöglichen
5. **Mocken Sie externe Abhängigkeiten**, um konsistente Testbedingungen zu gewährleisten 