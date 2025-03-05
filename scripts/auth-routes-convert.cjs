const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Define paths
const inputFile = '/app/src/server/routes/auth.ts';
const outputDir = '/app/src/server/dist/routes';
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

// Convert ES module imports to CommonJS
tsCode = tsCode.replace(
  /import\s+(\w+)\s+from\s+['"]([^'"]+)['"]/g,
  'const $1 = require("$2")'
);

// Convert named imports
tsCode = tsCode.replace(
  /import\s+\{\s*([^}]+)\s*\}\s+from\s+['"]([^'"]+)['"]/g,
  (match, imports, source) => {
    const importItems = imports
      .split(',')
      .map(item => item.trim())
      .filter(item => item);
    
    return `const { ${importItems.join(', ')} } = require("${source}")`;
  }
);

// Remove interface declarations and type annotations
tsCode = tsCode.replace(/interface\s+\w+\s*\{[^}]*\}/g, '');
tsCode = tsCode.replace(/:\s*\w+(\[\])?/g, '');

// Convert export default to module.exports
tsCode = tsCode.replace(/export\s+default\s+(\w+)/g, 'module.exports = $1');

// Write the converted JavaScript to the output file
console.log(`Writing converted JavaScript to: ${outputFile}`);
fs.writeFileSync(outputFile, tsCode);

// Check for syntax errors
try {
  execSync(`node --check "${outputFile}"`);
  console.log('No syntax errors found in the converted JavaScript file.');
} catch (error) {
  console.error('Syntax error in the converted JavaScript file:', error.message);
  process.exit(1);
}

console.log('Auth routes file conversion completed successfully.'); 