const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Define input and output paths
const inputFile = '/app/src/server/routes/bookmark.ts';
const outputDir = '/app/src/server/dist/routes';
const outputFile = path.join(outputDir, 'bookmark.js');

console.log(`Converting bookmark routes from ${inputFile} to ${outputFile}`);

// Create output directory if it doesn't exist
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`Created directory: ${outputDir}`);
}

try {
  // Read the TypeScript file
  let tsContent = fs.readFileSync(inputFile, 'utf8');
  
  // Remove any stray % character at the end if present
  tsContent = tsContent.replace(/%$/, '');
  
  // Convert TypeScript to JavaScript
  const jsContent = `const express = require('express');
const { 
  getBookmarks, 
  getBookmark, 
  createBookmark, 
  updateBookmark, 
  deleteBookmark 
} = require('../controllers/bookmark');
const { authMiddleware } = require('../middleware/auth');
const asyncHandler = require('express-async-handler');

const router = express.Router();

// All routes require authentication
router.use(authMiddleware);

// CRUD operations for Bookmarks
router.get('/', asyncHandler(getBookmarks));
router.get('/:id', asyncHandler(getBookmark));
router.post('/', asyncHandler(createBookmark));
router.put('/:id', asyncHandler(updateBookmark));
router.delete('/:id', asyncHandler(deleteBookmark));

module.exports = router;`;

  // Write the JavaScript file
  fs.writeFileSync(outputFile, jsContent);
  console.log(`Successfully wrote file: ${outputFile}`);
  
  // Check for syntax errors
  try {
    execSync(`node --check ${outputFile}`);
    console.log(`No syntax errors found in ${outputFile}`);
  } catch (error) {
    console.error(`Syntax error found in ${outputFile}:`, error.message);
    process.exit(1);
  }
  
  console.log('Bookmark routes conversion completed successfully');
} catch (error) {
  console.error('Error during bookmark routes conversion:', error);
  process.exit(1);
} 