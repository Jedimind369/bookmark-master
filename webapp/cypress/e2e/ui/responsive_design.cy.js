describe('Responsive UI Tests', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('sollte auf Desktop-Geräten korrekt angezeigt werden', () => {
    cy.viewport(1280, 800);
    
    // Hauptelemente sollten sichtbar sein
    cy.get('[data-testid="file-upload"]').should('be.visible');
    cy.get('[data-testid="start-processing-btn"]').should('be.visible');
    
    // Navigation sollte horizontal sein
    cy.get('nav').should('be.visible');
    cy.get('nav').find('ul').children().should('have.length.at.least', 3);
    
    // Sidebar sollte sichtbar sein (falls vorhanden)
    cy.get('[data-testid="sidebar"]').should('be.visible');
  });

  it('sollte auf Tablet-Geräten korrekt angezeigt werden', () => {
    cy.viewport('ipad-2');
    
    // Hauptelemente sollten sichtbar sein
    cy.get('[data-testid="file-upload"]').should('be.visible');
    cy.get('[data-testid="start-processing-btn"]').should('be.visible');
    
    // Navigation sollte noch sichtbar sein
    cy.get('nav').should('be.visible');
  });

  it('sollte auf Mobilgeräten korrekt angezeigt werden', () => {
    cy.viewport('iphone-x');
    
    // Mobile Menü-Button sollte sichtbar sein
    cy.get('[data-testid="mobile-menu-btn"]').should('be.visible');
    
    // Hauptelemente sollten angepasst sein
    cy.get('[data-testid="file-upload"]').should('be.visible');
    cy.get('[data-testid="start-processing-btn"]').should('be.visible');
    
    // Menü sollte ausklappbar sein
    cy.get('[data-testid="mobile-menu-btn"]').click();
    cy.get('nav').should('be.visible');
    
    // Sidebar sollte ausgeblendet oder angepasst sein
    cy.get('[data-testid="sidebar"]').should('not.be.visible');
  });

  it('sollte Formularelemente responsiv anpassen', () => {
    // Desktop
    cy.viewport(1280, 800);
    cy.get('form').should('have.css', 'flex-direction', 'row');
    
    // Tablet
    cy.viewport('ipad-2');
    cy.get('form').should('have.css', 'flex-direction', 'row');
    
    // Mobile
    cy.viewport('iphone-x');
    cy.get('form').should('have.css', 'flex-direction', 'column');
  });

  it('sollte Schriftgrößen responsiv anpassen', () => {
    // Desktop
    cy.viewport(1280, 800);
    cy.get('h1').should('have.css', 'font-size', '32px');
    
    // Mobile
    cy.viewport('iphone-x');
    cy.get('h1').should('have.css', 'font-size', '24px');
  });
}); 