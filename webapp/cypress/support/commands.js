// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************

// Import cypress-file-upload für Datei-Upload-Tests
import 'cypress-file-upload';

// Befehl zum Warten auf Verarbeitung mit Timeout
Cypress.Commands.add('waitForProcessing', (timeout = 30000) => {
  const checkInterval = 500;
  const maxAttempts = timeout / checkInterval;
  let attempts = 0;

  const checkStatus = () => {
    attempts++;
    return cy.get('[data-testid="processing-status"]', { timeout: 1000 })
      .then($status => {
        const text = $status.text();
        if (text.includes('abgeschlossen') || text.includes('completed')) {
          return;
        } else if (attempts >= maxAttempts) {
          throw new Error(`Verarbeitung nicht abgeschlossen nach ${timeout}ms`);
        } else {
          cy.wait(checkInterval);
          return checkStatus();
        }
      });
  };

  return checkStatus();
});

// Befehl zum Überprüfen der Metriken im Prometheus-Format
Cypress.Commands.add('checkMetric', (metricName, expectedValue) => {
  cy.request(`${Cypress.env('apiUrl')}/metrics`)
    .then((response) => {
      const metrics = response.body;
      const metricLine = metrics.split('\n').find(line => 
        line.startsWith(metricName) && !line.startsWith(`${metricName}_`)
      );
      
      if (!metricLine) {
        throw new Error(`Metrik ${metricName} nicht gefunden`);
      }
      
      const value = parseFloat(metricLine.split(' ')[1]);
      expect(value).to.be.closeTo(expectedValue, 0.1);
    });
});

// Befehl zum Simulieren von Netzwerkproblemen
Cypress.Commands.add('simulateNetworkIssue', (method, url, options = {}) => {
  const { delay = 2000, statusCode = 500, response = {} } = options;
  
  cy.intercept(method, url, (req) => {
    req.on('response', (res) => {
      // Verzögern und dann mit Fehler antworten
      res.setDelay(delay);
      res.send(statusCode, response);
    });
  });
}); 