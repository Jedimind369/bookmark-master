const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// Create the output directory
const outputDir = path.join('/app', 'src/server/dist');
fs.mkdirSync(outputDir, { recursive: true });

// Process all TypeScript files in the src/server directory
function processDirectory(directory) {
  console.log(`Processing directory: ${directory}`);
  const files = fs.readdirSync(directory);
  
  for (const file of files) {
    const filePath = path.join(directory, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory()) {
      // Skip dist directory to avoid infinite recursion
      if (file === 'dist' || file === 'node_modules' || file === 'coverage') {
        console.log(`Skipping directory: ${filePath}`);
        continue;
      }
      
      // Create the corresponding directory in the dist folder
      const distDir = path.join(outputDir, path.relative('/app/src/server', directory), file);
      console.log(`Creating directory: ${distDir}`);
      fs.mkdirSync(distDir, { recursive: true });
      
      // Process subdirectory
      processDirectory(filePath);
    } else if (file.endsWith('.ts')) {
      convertTsFile(filePath);
    } else if (file.endsWith('.json')) {
      // Copy JSON files to the dist directory
      const distPath = path.join(outputDir, path.relative('/app/src/server', directory), file);
      console.log(`Copying JSON file: ${filePath} -> ${distPath}`);
      fs.copyFileSync(filePath, distPath);
    }
  }
}

function convertTsFile(filePath) {
  console.log(`Converting ${filePath}`);
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Remove stray % character if it exists
  content = content.replace(/\s*%\s*$/, '');
  
  // 1. Convert import statements from ES module syntax to CommonJS
  content = content.replace(/import\s+(\{[^}]+\})\s+from\s+['"]([^'"]+)['"]/g, 
    (_, imports, module) => `const ${imports} = require('${module}')`);
  
  content = content.replace(/import\s+(\w+)\s+from\s+['"]([^'"]+)['"]/g, 
    (_, importName, module) => `const ${importName} = require('${module}')`);
  
  // 2. Remove interface and type declarations completely
  content = content.replace(/interface\s+\w+\s*\{[\s\S]*?\}\s*/g, '');
  content = content.replace(/type\s+\w+\s*=[\s\S]*?;\s*/g, '');
  
  // 3. Remove type annotations
  content = content.replace(/:\s*[A-Za-z0-9_<>[\]|&.]+(\[\])?/g, '');
  content = content.replace(/\s*<[^>]+>/g, '');
  content = content.replace(/:\s*Promise<[^>]+>/g, '');
  content = content.replace(/:\s*void/g, '');
  
  // 4. Handle export statements
  if (content.includes('export {')) {
    // Extract the exported items
    const exportMatch = content.match(/export\s+\{([^}]+)\}/);
    if (exportMatch) {
      const exportedItems = exportMatch[1].split(',').map(item => item.trim());
      content = content.replace(/export\s+\{([^}]+)\}/g, `module.exports = { ${exportedItems.join(', ')} }`);
    }
  } else {
    // Handle individual exports
    content = content.replace(/export\s+default\s+(\w+)/g, 'module.exports = $1');
    content = content.replace(/export\s+const\s+(\w+)/g, 'const $1');
    content = content.replace(/export\s+function\s+(\w+)/g, 'function $1');
    content = content.replace(/export\s+class\s+(\w+)/g, 'class $1');
    
    // Add module.exports at the end if there are individual exports
    if (content.match(/export\s+(const|function|class)\s+\w+/)) {
      const exportedNames = [];
      const exportMatches = content.matchAll(/export\s+(const|function|class)\s+(\w+)/g);
      for (const match of exportMatches) {
        exportedNames.push(match[2]);
      }
      
      if (exportedNames.length > 0) {
        content = content.replace(/export\s+(const|function|class)\s+(\w+)/g, '$1 $2');
        content += `\nmodule.exports = { ${exportedNames.join(', ')} };\n`;
      }
    }
  }
  
  // 5. Special handling for specific files
  if (filePath.includes('index.ts')) {
    // Fix error handler middleware
    content = content.replace(
      /app\.use\(\(error, req, res, next\)\s*=>\s*\{[\s\S]*?res\.status[\s\S]*?\}\);/g,
      `app.use((error, req, res, next) => {
  const statusCode = error.statusCode || 500;
  const message = error.message || 'Internal Server Error';
  console.error(error);
  res.status(statusCode).json({ 
    error: message,
    stack: process.env.NODE_ENV === 'development' ? error.stack : undefined 
  });
});`
    );

    // Fix route handlers
    content = content.replace(
      /app\.get\('\/'\, \(req\, res\) => \{\s*res\.json\(\{ message\);\s*\}\);/g,
      "app.get('/', (req, res) => {\n  res.json({ message: 'Bookmark Master API' });\n});"
    );

    content = content.replace(
      /app\.get\('\/api\/health'\, \(_req\, res\) => \{\s*res\.json\(\{ status\);\s*\}\);/g,
      "app.get('/api/health', (_req, res) => {\n  res.json({ status: 'ok' });\n});"
    );

    // Fix CORS configuration
    content = content.replace(
      /app\.use\(cors\(\{\s*origin: process\.env\.CORS_ORIGIN \|\| '\*',\s*\}\)\);/g,
      "app.use(cors({ origin: process.env.CORS_ORIGIN || '*' }));"
    );
  }
  
  // Special handling for auth controller
  if (filePath.includes('controllers/auth.ts')) {
    // Make sure we don't have any stray closing braces
    content = content.replace(/^\s*}\s*$/gm, '');
    
    // Fix destructuring in register function
    content = content.replace(
      /const \{ email, password, name \}(\s*) = req\.body;/g,
      'const { email, password, name } = req.body;'
    );
    
    // Fix destructuring in login function
    content = content.replace(
      /const \{ email, password \}(\s*) = req\.body;/g,
      'const { email, password } = req.body;'
    );
    
    // Fix password destructuring in responses
    content = content.replace(
      /const \{ password: _, ...userWithoutPassword \} = user;/g,
      'const { password: _, ...userWithoutPassword } = user;'
    );
    
    // Fix password destructuring in getMe
    content = content.replace(
      /const \{ password, ...userWithoutPassword \} = user;/g,
      'const { password, ...userWithoutPassword } = user;'
    );
  }
  
  // Write the converted JavaScript to the dist directory
  const relativePath = path.relative('/app/src/server', filePath);
  const outputPath = path.join(outputDir, relativePath.replace(/\.ts$/, '.js'));
  console.log(`Writing to: ${outputPath}`);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, content);
}

// Start the conversion process
processDirectory('/app/src/server');

console.log('Conversion completed. Output saved to src/server/dist/');

// Check for syntax errors in the converted JavaScript files
try {
  console.log('Checking for syntax errors in the converted JavaScript files...');
  execSync('node --check /app/src/server/dist/index.js', { stdio: 'inherit' });
  console.log('No syntax errors found in the main index.js file.');
  
  // Check auth.js specifically
  execSync('node --check /app/src/server/dist/controllers/auth.js', { stdio: 'inherit' });
  console.log('No syntax errors found in the auth.js file.');
} catch (error) {
  console.error('Syntax errors found:', error.message);
} 