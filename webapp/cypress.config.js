const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    viewportWidth: 1280,
    viewportHeight: 720,
    video: true,
    screenshotOnRunFailure: true,
    defaultCommandTimeout: 10000,
    requestTimeout: 15000,
    setupNodeEvents(on, config) {
      // Hier können Event-Listener hinzugefügt werden
      on('task', {
        log(message) {
          console.log(message);
          return null;
        }
      });
    }
  },
  env: {
    apiUrl: 'http://localhost:5000'
  }
}); 