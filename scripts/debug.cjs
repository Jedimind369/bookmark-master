const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Create a simple Docker container to check the converted file
const dockerCommand = `
FROM bookmark-master-app
WORKDIR /app
CMD cat /app/src/server/dist/index.js
`;

// Write the Dockerfile
fs.writeFileSync('Dockerfile.debug', dockerCommand);

try {
  console.log('Building debug container...');
  execSync('docker build -f Dockerfile.debug -t bookmark-debug .', { stdio: 'inherit' });
  
  console.log('\nRunning debug container to check the converted file:');
  const output = execSync('docker run --rm bookmark-debug', { encoding: 'utf-8' });
  
  // Write the output to a file for inspection
  fs.writeFileSync('debug-output.js', output);
  console.log('\nConverted JavaScript file has been saved to debug-output.js');
  
  // Check for syntax errors
  console.log('\nChecking for syntax errors...');
  try {
    // Try to parse the JavaScript
    require('vm').runInNewContext(output, {}, { filename: 'index.js' });
    console.log('No syntax errors found in the JavaScript code.');
  } catch (syntaxError) {
    console.error('Syntax error found:', syntaxError.message);
    console.error('Line:', syntaxError.lineNumber, 'Column:', syntaxError.columnNumber);
    
    // Show the problematic lines
    const lines = output.split('\n');
    const startLine = Math.max(0, syntaxError.lineNumber - 3);
    const endLine = Math.min(lines.length, syntaxError.lineNumber + 3);
    
    console.log('\nProblematic code section:');
    for (let i = startLine; i < endLine; i++) {
      const lineNum = i + 1;
      const marker = lineNum === syntaxError.lineNumber ? '> ' : '  ';
      console.log(`${marker}${lineNum}: ${lines[i]}`);
    }
  }
} catch (error) {
  console.error('Error:', error.message);
} 