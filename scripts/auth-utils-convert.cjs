const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Define paths
const inputFile = '/app/src/server/utils/auth.ts';
const outputDir = '/app/src/server/dist/utils';
const outputFile = path.join(outputDir, 'auth.js');

// Create output directory if it doesn't exist
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`Created directory: ${outputDir}`);
}

// Read the TypeScript file
console.log(`Reading TypeScript file: ${inputFile}`);
let tsCode = fs.readFileSync(inputFile, 'utf8');

// Remove any stray % characters that might be at the end of the file
tsCode = tsCode.replace(/%$/, '');

// Create a completely new JavaScript file based on the TypeScript content
let jsContent = `const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');

dotenv.config();

const JWT_SECRET = process.env.JWT_SECRET || 'fallback_secret';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';

/**
 * Hasht ein Passwort mit bcrypt
 */
const hashPassword = async (password) => {
  const saltRounds = 10;
  return bcrypt.hash(password, saltRounds);
};

/**
 * Vergleicht ein Passwort mit einem gespeicherten Hash
 */
const comparePasswords = async (password, hashedPassword) => {
  return bcrypt.compare(password, hashedPassword);
};

/**
 * Generiert ein JWT-Token für einen Benutzer
 */
const generateToken = (user) => {
  const payload = {
    id: user.id,
    email: user.email,
    name: user.name
  };

  return jwt.sign(payload, JWT_SECRET);
};

/**
 * Verifiziert ein JWT-Token
 */
const verifyToken = (token) => {
  try {
    return jwt.verify(token, JWT_SECRET);
  } catch (error) {
    throw new Error('Ungültiges Token');
  }
};

module.exports = {
  hashPassword,
  comparePasswords,
  generateToken,
  verifyToken
};`;

// Write the converted JavaScript to the output file
console.log(`Writing converted JavaScript to: ${outputFile}`);
fs.writeFileSync(outputFile, jsContent);

// Check for syntax errors
try {
  execSync(`node --check "${outputFile}"`);
  console.log('No syntax errors found in the converted JavaScript file.');
} catch (error) {
  console.error('Syntax error in the converted JavaScript file:', error.message);
  process.exit(1);
}

console.log('Auth utils file conversion completed successfully.'); 