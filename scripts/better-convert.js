const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Read the original TypeScript file
const tsContent = fs.readFileSync('original-index.ts', 'utf8');

// Perform the conversion
let jsContent = tsContent;

// Convert imports
jsContent = jsContent.replace(/import ([a-zA-Z0-9_]+) from ['"]([^'"]+)['"];/g, 'const $1 = require("$2");');
jsContent = jsContent.replace(/import \{ ([^}]+) \} from ['"]([^'"]+)['"];/g, 'const { $1 } = require("$2");');

// Convert exports
jsContent = jsContent.replace(/export const/g, 'const');
jsContent = jsContent.replace(/export default/g, 'module.exports =');
jsContent = jsContent.replace(/export \{/g, 'module.exports = {');

// Remove type annotations
jsContent = jsContent.replace(/: [A-Za-z<>\[\]|&]+/g, '');
jsContent = jsContent.replace(/: any(\[\])?/g, '');
jsContent = jsContent.replace(/: (string|number|boolean|void|object|unknown|never|null|undefined)/g, '');

// Fix error handler middleware
jsContent = jsContent.replace(/app\.use\(\(err: any, req: express\.Request, res: express\.Response, next: express\.NextFunction\) =>/g, 'app.use((err, req, res, next) =>');
jsContent = jsContent.replace(/app\.use\(\(err, req\.Request, res\.Response, next\.NextFunction\) =>/g, 'app.use((err, req, res, next) =>');

// Fix route handlers
jsContent = jsContent.replace(/\(req: express\.Request, res: express\.Response(?:, next: express\.NextFunction)?\) =>/g, '(req, res, next) =>');
jsContent = jsContent.replace(/\(_req: express\.Request, res: express\.Response(?:, next: express\.NextFunction)?\) =>/g, '(_req, res, next) =>');

// Fix CORS configuration
jsContent = jsContent.replace(/app\.use\(cors\(\{[^}]*\}\)\);/g, `app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:3001'],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));`);

// Fix JSON responses
jsContent = jsContent.replace(/res\.json\(\{ message\);/g, "res.json({ message: 'Bookmark Master API' });");
jsContent = jsContent.replace(/res\.json\(\{ status\);/g, "res.json({ status: 'ok' });");

// Remove interface and type declarations
jsContent = jsContent.split('\n').filter(line => !line.startsWith('interface ') && !line.startsWith('type ')).join('\n');

// Write the converted JavaScript file
fs.writeFileSync('better-converted-index.js', jsContent);

console.log('Conversion completed. Output saved to better-converted-index.js');

// Check for syntax errors
try {
  execSync('node --check better-converted-index.js', { stdio: 'inherit' });
  console.log('No syntax errors found in the converted JavaScript file.');
} catch (error) {
  console.error('Syntax errors found in the converted JavaScript file.');
} 