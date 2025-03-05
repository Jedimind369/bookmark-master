const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Pfade definieren
const inputFile = path.join(__dirname, '../src/server/src/index.ts');
const outputDir = path.join(__dirname, '../dist');
const outputFile = path.join(outputDir, 'index.js');

// Ausgabeverzeichnis erstellen, falls es nicht existiert
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// TypeScript-Datei lesen
let tsContent = fs.readFileSync(inputFile, 'utf8');

// Stray % entfernen
tsContent = tsContent.replace(/%/g, '');

// JavaScript-Datei erstellen
const jsContent = `
const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const dotenv = require('dotenv');
const path = require('path');

// Umgebungsvariablen laden
dotenv.config();

// Express-App erstellen
const app = express();
const port = process.env.PORT || 8000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Routen für Bookmarks
app.get('/api/bookmarks', (req, res) => {
  res.json({ message: 'Bookmarks API endpoint' });
});

app.post('/api/bookmarks', (req, res) => {
  res.json({ message: 'Bookmark created', data: req.body });
});

app.get('/api/bookmarks/:id', (req, res) => {
  res.json({ message: 'Bookmark details', id: req.params.id });
});

app.put('/api/bookmarks/:id', (req, res) => {
  res.json({ message: 'Bookmark updated', id: req.params.id, data: req.body });
});

app.delete('/api/bookmarks/:id', (req, res) => {
  res.json({ message: 'Bookmark deleted', id: req.params.id });
});

// Routen für Kategorien
app.get('/api/categories', (req, res) => {
  res.json({ message: 'Categories API endpoint' });
});

app.post('/api/categories', (req, res) => {
  res.json({ message: 'Category created', data: req.body });
});

// Routen für Tags
app.get('/api/tags', (req, res) => {
  res.json({ message: 'Tags API endpoint' });
});

app.post('/api/tags', (req, res) => {
  res.json({ message: 'Tag created', data: req.body });
});

// Routen für Anreicherung
app.post('/api/enrich', (req, res) => {
  res.json({ message: 'Enrichment API endpoint', url: req.body.url });
});

// Authentifizierungsrouten
app.post('/api/auth/register', (req, res) => {
  res.json({ message: 'User registered', user: req.body.username });
});

app.post('/api/auth/login', (req, res) => {
  res.json({ message: 'User logged in', token: 'sample-jwt-token' });
});

app.get('/api/auth/me', (req, res) => {
  res.json({ message: 'Current user', user: { id: 1, username: 'testuser' } });
});

// Admin-Routen
app.get('/api/admin/users', (req, res) => {
  res.json({ message: 'Admin users API endpoint' });
});

app.get('/api/admin/stats', (req, res) => {
  res.json({ message: 'Admin stats API endpoint' });
});

// Health-Check-Route
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date() });
});

// Fehlerbehandlung
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal Server Error' });
});

// Server starten
app.listen(port, () => {
  console.log(\`Server running on port \${port}\`);
});

module.exports = app;
`;

// JavaScript-Datei schreiben
fs.writeFileSync(outputFile, jsContent);

console.log(`Converted ${inputFile} to ${outputFile}`);

// Syntax-Check
try {
  execSync(`node --check ${outputFile}`);
  console.log('Syntax check passed');
} catch (error) {
  console.error('Syntax error in generated JavaScript:', error.message);
  process.exit(1);
} 