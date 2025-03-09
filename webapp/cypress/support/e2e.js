// ***********************************************************
// This example support/e2e.js is processed and
// loaded automatically before your test files.
//
// This is a great place to put global configuration and
// behavior that modifies Cypress.
//
// You can change the location of this file or turn off
// automatically serving support files with the
// 'supportFile' configuration option.
//
// You can read more here:
// https://on.cypress.io/configuration
// ***********************************************************

// Import commands.js using ES2015 syntax:
import './commands';

// Globale Fehlerbehandlung
Cypress.on('uncaught:exception', (err, runnable) => {
  // Verhindert, dass Cypress bei unbehandelten Ausnahmen im Frontend abbricht
  // Dies ist nützlich, wenn wir Fehlerszenarien testen
  console.error('Unbehandelte Ausnahme:', err.message);
  return false;
});

// Globale Einstellungen für alle Tests
beforeEach(() => {
  // Setze einen konsistenten Ausgangszustand für jeden Test
  cy.clearLocalStorage();
  cy.clearCookies();
  
  // Füge data-testid-Attribute für Elemente hinzu, die keine haben
  // Dies ist nützlich, wenn wir mit einer bestehenden Anwendung arbeiten
  Cypress.on('window:before:load', (win) => {
    const originalAppendChild = win.Element.prototype.appendChild;
    win.Element.prototype.appendChild = function appendChild(element) {
      if (element.tagName === 'BUTTON' && !element.hasAttribute('data-testid')) {
        // Füge data-testid basierend auf Text oder Klasse hinzu
        const buttonText = element.textContent?.trim();
        if (buttonText) {
          element.setAttribute('data-testid', `button-${buttonText.toLowerCase().replace(/\s+/g, '-')}`);
        }
      }
      return originalAppendChild.call(this, element);
    };
  });
}); 