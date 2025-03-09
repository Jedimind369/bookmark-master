describe('Performance- und Last-Tests', () => {
  beforeEach(() => {
    // Mocks für API-Aufrufe vorbereiten
    cy.intercept('POST', '/api/process/json', (req) => {
      // Simuliere eine längere Verarbeitung für große Dateien
      const requestBody = req.body;
      const isLargeFile = requestBody && requestBody.file_path && requestBody.file_path.includes('large');
      
      if (isLargeFile) {
        // Verzögere die Antwort für große Dateien
        req.reply({
          delay: 3000,
          statusCode: 200,
          body: { 
            success: true, 
            itemsProcessed: 1000,
            outputPath: '/data/processed/large_bookmarks_processed.json'
          }
        });
      } else {
        req.reply({
          statusCode: 200,
          body: { 
            success: true, 
            itemsProcessed: 5,
            outputPath: '/data/processed/bookmarks_processed.json'
          }
        });
      }
    }).as('processJson');
    
    cy.visit('/');
  });

  it('sollte Fortschrittsanzeige während der Verarbeitung aktualisieren', () => {
    // Setup für kontinuierliche Statusupdates vom Processor
    const statusUpdates = [10, 30, 50, 70, 90, 100].map(progress => ({
      body: {
        progress: progress,
        total: 100,
        status: progress < 100 ? 'processing' : 'completed'
      }
    }));
    
    let updateIndex = 0;
    cy.intercept('GET', '/api/status?*', (req) => {
      // Simuliere Statusupdates in Echtzeit
      if (updateIndex < statusUpdates.length) {
        req.reply(statusUpdates[updateIndex]);
        updateIndex++;
      } else {
        req.reply(statusUpdates[statusUpdates.length - 1]);
      }
    }).as('statusCheck');
    
    // Große Datei simulieren
    cy.get('[data-testid="file-upload"]').attachFile({
      fileContent: JSON.stringify(Array(1000).fill().map((_, i) => ({
        url: `https://example.com/page${i}`,
        title: `Page ${i}`,
        description: `Description for page ${i}`
      }))),
      fileName: 'large_bookmarks.json',
      mimeType: 'application/json'
    });
    
    // Verarbeitung starten
    cy.get('[data-testid="start-processing-btn"]').click();
    
    // Prüfen, ob Progressbar angezeigt wird
    cy.get('[data-testid="progress-bar"]').should('be.visible');
    
    // Prüfen, ob Statusupdates korrekt verarbeitet werden
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '10');
    
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '30');
    
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '50');
    
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '70');
    
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '90');
    
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '100');
    
    // Prüfen, ob UI bei Abschluss korrekt aktualisiert wird
    cy.get('[data-testid="status-message"]').should('contain', 'Verarbeitung abgeschlossen');
  });

  it('sollte UI-Reaktionsfähigkeit während der Verarbeitung beibehalten', () => {
    // Simuliere eine sehr lange Verarbeitung
    cy.intercept('POST', '/api/process/json', {
      delay: 5000, // 5 Sekunden Verzögerung
      statusCode: 200,
      body: { 
        success: true, 
        itemsProcessed: 10000,
        outputPath: '/data/processed/large_bookmarks_processed.json'
      }
    }).as('longProcessing');
    
    // Datei hochladen und Verarbeitung starten
    cy.get('[data-testid="file-upload"]').attachFile('bookmarks.json');
    cy.get('[data-testid="start-processing-btn"]').click();
    
    // Während der Verarbeitung sollte die UI reaktionsfähig bleiben
    cy.get('[data-testid="cancel-btn"]').should('be.visible').and('be.enabled');
    cy.get('[data-testid="settings-btn"]').should('be.visible').and('be.enabled').click();
    
    // Einstellungen sollten angezeigt werden können
    cy.get('[data-testid="settings-panel"]').should('be.visible');
    cy.get('[data-testid="max-workers-input"]').should('be.visible').and('be.enabled');
    
    // Einstellungen schließen
    cy.get('[data-testid="close-settings-btn"]').click();
    cy.get('[data-testid="settings-panel"]').should('not.be.visible');
    
    // Warten auf Abschluss der Verarbeitung
    cy.wait('@longProcessing');
    cy.get('[data-testid="processing-status"]').should('contain', 'Verarbeitung abgeschlossen');
  });

  it('sollte mehrere gleichzeitige Anfragen korrekt verarbeiten', () => {
    // Simuliere mehrere gleichzeitige Verarbeitungen
    let requestCount = 0;
    cy.intercept('POST', '/api/process/json', (req) => {
      requestCount++;
      req.reply({
        statusCode: 200,
        body: { 
          success: true, 
          itemsProcessed: 5,
          outputPath: `/data/processed/bookmarks_${requestCount}.json`
        }
      });
    }).as('processRequest');
    
    // Erste Datei hochladen und verarbeiten
    cy.get('[data-testid="file-upload"]').attachFile('bookmarks.json');
    cy.get('[data-testid="start-processing-btn"]').click();
    
    // Zweite Datei in neuem Tab hochladen
    cy.window().then((win) => {
      cy.stub(win, 'open').as('windowOpen').returns({
        location: { href: '' },
        document: win.document
      });
    });
    
    cy.get('[data-testid="new-tab-btn"]').click();
    cy.get('@windowOpen').should('be.called');
    
    // Simuliere zweite Verarbeitung
    cy.get('[data-testid="file-upload"]').attachFile('bookmarks.json');
    cy.get('[data-testid="start-processing-btn"]').click();
    
    // Beide Anfragen sollten erfolgreich sein
    cy.wait('@processRequest');
    cy.wait('@processRequest');
    
    // Überprüfe, ob beide Verarbeitungen abgeschlossen wurden
    cy.get('[data-testid="processing-status"]').should('contain', 'Verarbeitung abgeschlossen');
  });

  it('sollte bei Netzwerkproblemen angemessen reagieren', () => {
    // Simuliere Netzwerkprobleme
    cy.intercept('POST', '/api/process/json', {
      forceNetworkError: true
    }).as('networkError');
    
    // Datei hochladen und Verarbeitung starten
    cy.get('[data-testid="file-upload"]').attachFile('bookmarks.json');
    cy.get('[data-testid="start-processing-btn"]').click();
    
    // Fehlerbehandlung überprüfen
    cy.wait('@networkError');
    cy.get('[data-testid="error-message"]').should('be.visible');
    cy.get('[data-testid="error-message"]').should('contain', 'Netzwerkfehler');
    cy.get('[data-testid="retry-btn"]').should('be.visible');
    
    // Retry-Funktionalität testen
    cy.intercept('POST', '/api/process/json', {
      statusCode: 200,
      body: { 
        success: true, 
        itemsProcessed: 5,
        outputPath: '/data/processed/bookmarks_processed.json'
      }
    }).as('retryRequest');
    
    cy.get('[data-testid="retry-btn"]').click();
    cy.wait('@retryRequest');
    cy.get('[data-testid="processing-status"]').should('contain', 'Verarbeitung abgeschlossen');
  });
}); 