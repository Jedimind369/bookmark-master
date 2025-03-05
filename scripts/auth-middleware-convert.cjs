const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Define paths
const outputDir = '/app/src/server/dist/middleware';
const outputFile = path.join(outputDir, 'auth.js');

console.log(`Creating auth middleware file at ${outputFile}`);

// Create output directory if it doesn't exist
if (!fs.existsSync(outputDir)) {
  console.log(`Creating directory: ${outputDir}`);
  fs.mkdirSync(outputDir, { recursive: true });
}

// Manually create the JavaScript content
const jsContent = `
const { Request, Response, NextFunction } = require('express');
const { verifyToken } = require('../utils/auth');
const { prisma } = require('../index');

/**
 * Middleware zum Schutz von Routen, die Authentifizierung erfordern
 */
const authMiddleware = async (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(401).json({ error: 'Kein Authentifizierungstoken bereitgestellt' });
      return;
    }
    
    const token = authHeader.split(' ')[1];
    const decoded = verifyToken(token);
    
    // Überprüfe, ob der Benutzer noch existiert
    const user = await prisma.user.findUnique({
      where: { id: decoded.id }
    });
    
    if (!user) {
      res.status(401).json({ error: 'Benutzer existiert nicht mehr' });
      return;
    }
    
    // Füge die Benutzer-ID zum Request-Objekt hinzu, damit nachfolgende Handler darauf zugreifen können
    req.userId = decoded.id;
    
    next();
  } catch (error) {
    res.status(401).json({ error: 'Nicht autorisiert' });
  }
};

module.exports = { authMiddleware };
`;

// Write the JavaScript file
fs.writeFileSync(outputFile, jsContent);
console.log(`Successfully wrote ${outputFile}`);

// Check for syntax errors
try {
  execSync(`node --check ${outputFile}`);
  console.log(`No syntax errors found in ${outputFile}`);
} catch (error) {
  console.error(`Syntax errors found in ${outputFile}`);
  process.exit(1);
}

console.log('Auth middleware conversion completed successfully'); 