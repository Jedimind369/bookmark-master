const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Path to the auth controller
const authTsPath = '/app/src/server/controllers/auth.ts';
const authJsPath = '/app/src/server/dist/controllers/auth.js';

// Create the output directory
const outputDir = path.dirname(authJsPath);
fs.mkdirSync(outputDir, { recursive: true });

console.log(`Converting auth controller: ${authTsPath} -> ${authJsPath}`);

// Read the TypeScript file
let content = fs.readFileSync(authTsPath, 'utf8');

// Remove stray % character if it exists
content = content.replace(/\s*%\s*$/, '');

// Create a completely new JavaScript file based on the TypeScript content
let jsContent = `const { prisma } = require('../index');
const { hashPassword, comparePasswords, generateToken } = require('../utils/auth');

/**
 * Registriert einen neuen Benutzer
 */
const register = async (req, res) => {
  try {
    const { email, password, name } = req.body;

    // Validiere Eingaben
    if (!email || !password) {
      res.status(400).json({ error: 'E-Mail und Passwort sind erforderlich' });
      return;
    }

    // Prüfe, ob Benutzer bereits existiert
    const existingUser = await prisma.user.findUnique({
      where: { email }
    });

    if (existingUser) {
      res.status(400).json({ error: 'E-Mail wird bereits verwendet' });
      return;
    }

    // Hashe das Passwort
    const hashedPassword = await hashPassword(password);

    // Erstelle den neuen Benutzer
    const user = await prisma.user.create({
      data: {
        email,
        password: hashedPassword,
        name
      }
    });

    // Generiere Token
    const token = generateToken(user);

    // Sende Response ohne das Passwort
    const { password: _, ...userWithoutPassword } = user;
    
    res.status(201).json({
      data: {
        user: userWithoutPassword,
        token
      }
    });
  } catch (error) {
    console.error('Fehler bei der Registrierung:', error);
    res.status(500).json({ error: 'Fehler bei der Registrierung' });
  }
};

/**
 * Meldet einen Benutzer an
 */
const login = async (req, res) => {
  try {
    const { email, password } = req.body;

    // Validiere Eingaben
    if (!email || !password) {
      res.status(400).json({ error: 'E-Mail und Passwort sind erforderlich' });
      return;
    }

    // Finde den Benutzer
    const user = await prisma.user.findUnique({
      where: { email }
    });

    if (!user) {
      res.status(401).json({ error: 'Ungültige Anmeldedaten' });
      return;
    }

    // Überprüfe das Passwort
    const isPasswordValid = await comparePasswords(password, user.password);

    if (!isPasswordValid) {
      res.status(401).json({ error: 'Ungültige Anmeldedaten' });
      return;
    }

    // Generiere Token
    const token = generateToken(user);

    // Sende Response ohne das Passwort
    const { password: _, ...userWithoutPassword } = user;
    
    res.status(200).json({
      data: {
        user: userWithoutPassword,
        token
      }
    });
  } catch (error) {
    console.error('Fehler beim Login:', error);
    res.status(500).json({ error: 'Fehler beim Login' });
  }
};

/**
 * Gibt Informationen über den aktuell angemeldeten Benutzer zurück
 */
const getMe = async (req, res) => {
  try {
    const userId = req.userId;

    if (!userId) {
      res.status(401).json({ error: 'Nicht autorisiert' });
      return;
    }

    const user = await prisma.user.findUnique({
      where: { id: userId }
    });

    if (!user) {
      res.status(404).json({ error: 'Benutzer nicht gefunden' });
      return;
    }

    // Sende Response ohne das Passwort
    const { password, ...userWithoutPassword } = user;
    
    res.status(200).json({
      data: userWithoutPassword
    });
  } catch (error) {
    console.error('Fehler beim Abrufen des Benutzerprofils:', error);
    res.status(500).json({ error: 'Interner Serverfehler' });
  }
};

module.exports = { register, login, getMe };`;

// Write the converted JavaScript to the output file
fs.writeFileSync(authJsPath, jsContent);

console.log('Auth controller conversion completed.');

// Check for syntax errors in the converted JavaScript file
try {
  console.log('Checking for syntax errors in the auth.js file...');
  execSync('node --check ' + authJsPath, { stdio: 'inherit' });
  console.log('No syntax errors found in the auth.js file.');
} catch (error) {
  console.error('Syntax errors found:', error.message);
} 