/// <reference types="cypress" />

describe('Vollständiger Bookmark-Workflow', () => {
  beforeEach(() => {
    // Mocks für API-Aufrufe vorbereiten
    cy.intercept('POST', '/api/process/json', {
      statusCode: 200,
      body: { 
        success: true, 
        itemsProcessed: 5,
        outputPath: '/data/processed/bookmarks_processed.json'
      }
    }).as('processJson');
    
    cy.intercept('POST', '/api/report', {
      statusCode: 200,
      body: { 
        success: true, 
        outputPath: '/data/reports/report.html'
      }
    }).as('generateReport');
    
    cy.intercept('GET', '/api/stats', {
      statusCode: 200,
      body: {
        activeWorkers: 0,
        memoryUsageBytes: 52428800, // 50 MB
        requestsProcessed: 1,
        errorsTotal: 0,
        averageProcessingTime: 2.5,
        uptime: 3600
      }
    }).as('getStats');
    
    // Startseite besuchen
    cy.visit('/');
  });

  it('sollte Bookmarks hochladen, verarbeiten und einen Report generieren', () => {
    // 1. Datei hochladen
    cy.get('[data-testid="file-upload"]').attachFile({
      fileContent: JSON.stringify([
        { url: "https://example.com", title: "Example Website" },
        { url: "https://test.org", title: "Test Website" }
      ]),
      fileName: 'bookmarks.json',
      mimeType: 'application/json'
    });
    
    // 2. Verarbeitung starten
    cy.get('[data-testid="start-processing-btn"]').click();
    
    // 3. Auf Verarbeitung warten und Status überprüfen
    cy.wait('@processJson').its('response.statusCode').should('eq', 200);
    cy.get('[data-testid="processing-status"]').should('contain', 'Verarbeitung abgeschlossen');
    cy.get('[data-testid="items-processed"]').should('contain', '5');
    
    // 4. Report generieren
    cy.get('[data-testid="generate-report-btn"]').click();
    cy.wait('@generateReport').its('response.statusCode').should('eq', 200);
    
    // 5. Report-Link überprüfen
    cy.get('[data-testid="report-link"]')
      .should('be.visible')
      .and('have.attr', 'href')
      .and('include', 'report.html');
    
    // 6. Statistiken prüfen
    cy.get('[data-testid="show-stats-btn"]').click();
    cy.wait('@getStats');
    cy.get('[data-testid="memory-usage"]').should('contain', '50 MB');
    cy.get('[data-testid="avg-processing-time"]').should('contain', '2.5');
  });

  it('sollte Fehler beim Verarbeiten korrekt handhaben', () => {
    // Mock für Fehlerfall überschreiben
    cy.intercept('POST', '/api/process/json', {
      statusCode: 500,
      body: { 
        success: false, 
        error: "Fehler bei der Verarbeitung: Ungültiges JSON-Format"
      }
    }).as('processJsonError');
    
    // Datei hochladen und Verarbeitung starten
    cy.get('[data-testid="file-upload"]').attachFile('invalid_bookmarks.json');
    cy.get('[data-testid="start-processing-btn"]').click();
    
    // Fehlerbehandlung überprüfen
    cy.wait('@processJsonError');
    cy.get('[data-testid="error-message"]').should('be.visible');
    cy.get('[data-testid="error-message"]').should('contain', 'Ungültiges JSON-Format');
    cy.get('[data-testid="retry-btn"]').should('be.visible');
  });

  it('sollte große Dateien in Chunks verarbeiten und Fortschritt anzeigen', () => {
    // Mock für Statusupdates
    let progressCounter = 0;
    const progressSteps = [0, 20, 40, 60, 80, 100];
    
    cy.intercept('GET', '/api/status?*', (req) => {
      const progress = progressSteps[progressCounter];
      req.reply({
        statusCode: 200,
        body: {
          progress: progress,
          total: 100,
          status: progress < 100 ? 'processing' : 'completed'
        }
      });
      
      // Nächster Fortschrittsschritt für den nächsten Aufruf
      if (progressCounter < progressSteps.length - 1) {
        progressCounter++;
      }
    }).as('statusCheck');
    
    // Große Datei simulieren
    cy.get('[data-testid="file-upload"]').attachFile('bookmarks.json');
    cy.get('[data-testid="start-processing-btn"]').click();
    
    // Fortschrittsanzeige überprüfen
    cy.get('[data-testid="progress-bar"]').should('exist');
    
    // Warten auf Statusupdates und Fortschritt überprüfen
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '20');
    
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '40');
    
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '60');
    
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '80');
    
    cy.wait('@statusCheck');
    cy.get('[data-testid="progress-bar"]').should('have.attr', 'value', '100');
    
    // Abschluss überprüfen
    cy.get('[data-testid="processing-status"]').should('contain', 'Verarbeitung abgeschlossen');
  });
}); 