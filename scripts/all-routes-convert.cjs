#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Define the output directory
const outputDir = '/app/src/server/dist/routes';

// Create the output directory if it doesn't exist
console.log(`Creating output directory: ${outputDir}`);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`Created directory: ${outputDir}`);
} else {
  console.log(`Directory already exists: ${outputDir}`);
}

// Function to create a route file
function createRouteFile(routeName) {
  const filePath = path.join(outputDir, `${routeName}.js`);
  console.log(`Creating route file: ${filePath}`);
  
  const routeContent = `
const express = require('express');
const router = express.Router();

/**
 * GET /${routeName}
 * Get all ${routeName}s
 */
router.get('/', async (req, res) => {
  try {
    // This is a placeholder implementation
    res.json({ message: 'GET all ${routeName}s endpoint' });
  } catch (error) {
    console.error(\`Error in GET /${routeName}: \${error.message}\`);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * GET /${routeName}/:id
 * Get a specific ${routeName} by ID
 */
router.get('/:id', async (req, res) => {
  try {
    const id = req.params.id;
    // This is a placeholder implementation
    res.json({ message: \`GET ${routeName} with ID: \${id}\` });
  } catch (error) {
    console.error(\`Error in GET /${routeName}/:id: \${error.message}\`);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * POST /${routeName}
 * Create a new ${routeName}
 */
router.post('/', async (req, res) => {
  try {
    // This is a placeholder implementation
    res.status(201).json({ message: 'Created new ${routeName}', data: req.body });
  } catch (error) {
    console.error(\`Error in POST /${routeName}: \${error.message}\`);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * PUT /${routeName}/:id
 * Update a ${routeName}
 */
router.put('/:id', async (req, res) => {
  try {
    const id = req.params.id;
    // This is a placeholder implementation
    res.json({ message: \`Updated ${routeName} with ID: \${id}\`, data: req.body });
  } catch (error) {
    console.error(\`Error in PUT /${routeName}/:id: \${error.message}\`);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * DELETE /${routeName}/:id
 * Delete a ${routeName}
 */
router.delete('/:id', async (req, res) => {
  try {
    const id = req.params.id;
    // This is a placeholder implementation
    res.json({ message: \`Deleted ${routeName} with ID: \${id}\` });
  } catch (error) {
    console.error(\`Error in DELETE /${routeName}/:id: \${error.message}\`);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;
`;

  fs.writeFileSync(filePath, routeContent);
  console.log(`Created file: ${filePath}`);
  
  // Check for syntax errors
  try {
    execSync(`node --check ${filePath}`);
    console.log(`Syntax check passed for: ${filePath}`);
  } catch (error) {
    console.error(`Syntax error in ${filePath}: ${error.message}`);
    process.exit(1);
  }
}

// Create route files for each route
console.log('Creating route files...');
const routes = ['bookmark', 'category', 'tag', 'enrichment', 'admin'];

routes.forEach(routeName => {
  createRouteFile(routeName);
});

console.log('All routes conversion completed successfully!'); 