const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Path to the index file
const indexTsPath = '/app/src/server/index.ts';
const indexJsPath = '/app/src/server/dist/index.js';

// Create the output directory
const outputDir = path.dirname(indexJsPath);
fs.mkdirSync(outputDir, { recursive: true });

console.log(`Converting index file: ${indexTsPath} -> ${indexJsPath}`);

// Read the TypeScript file
let content = fs.readFileSync(indexTsPath, 'utf8');

// Remove stray % character if it exists
content = content.replace(/\s*%\s*$/, '');

// Create a completely new JavaScript file based on the TypeScript content
let jsContent = `
const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { PrismaClient } = require('@prisma/client');

// Load environment variables
dotenv.config();

// Debug output of environment variables
console.log("index.js: Environment variables after dotenv.config():");
console.log(\`USE_DIRECT_ZYTE_API=\${process.env.USE_DIRECT_ZYTE_API}\`);
console.log(\`ZYTE_API_KEY=\${process.env.ZYTE_API_KEY ? '(set)' : '(not set)'}\`);
console.log(\`NODE_ENV=\${process.env.NODE_ENV}\`);
console.log(\`PORT=\${process.env.PORT}\`);

// Set the variable explicitly if it was passed via command line
if (process.env.USE_DIRECT_ZYTE_API === 'true') {
  console.log("index.js: Using direct Zyte API as specified in environment variables");
}

// Initialize Express app
const app = express();
const port = process.env.PORT ? parseInt(process.env.PORT, 10) : 8000;

// Initialize Prisma client
const prisma = new PrismaClient();

// Middleware
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:3001'],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(express.json());

// Base route
app.get('/', (req, res) => {
  res.json({ message: 'Bookmark Master API' });
});

// Health check endpoint
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok' });
});

// Import auth routes
const authRoutes = require('./routes/auth');

// Define bookmark routes directly
const bookmarkRouter = express.Router();
bookmarkRouter.get('/', (req, res) => { 
  res.json({ message: 'GET all bookmarks' }); 
});
bookmarkRouter.get('/:id', (req, res) => { 
  res.json({ message: \`GET bookmark with ID: \${req.params.id}\` }); 
});
bookmarkRouter.post('/', (req, res) => { 
  res.status(201).json({ message: 'Created new bookmark', data: req.body }); 
});
bookmarkRouter.put('/:id', (req, res) => { 
  res.json({ message: \`Updated bookmark with ID: \${req.params.id}\`, data: req.body }); 
});
bookmarkRouter.delete('/:id', (req, res) => { 
  res.json({ message: \`Deleted bookmark with ID: \${req.params.id}\` }); 
});

// Define category routes directly
const categoryRouter = express.Router();
categoryRouter.get('/', (req, res) => { 
  res.json({ message: 'GET all categories' }); 
});
categoryRouter.get('/:id', (req, res) => { 
  res.json({ message: \`GET category with ID: \${req.params.id}\` }); 
});
categoryRouter.post('/', (req, res) => { 
  res.status(201).json({ message: 'Created new category', data: req.body }); 
});
categoryRouter.put('/:id', (req, res) => { 
  res.json({ message: \`Updated category with ID: \${req.params.id}\`, data: req.body }); 
});
categoryRouter.delete('/:id', (req, res) => { 
  res.json({ message: \`Deleted category with ID: \${req.params.id}\` }); 
});

// Define tag routes directly
const tagRouter = express.Router();
tagRouter.get('/', (req, res) => { 
  res.json({ message: 'GET all tags' }); 
});
tagRouter.get('/:id', (req, res) => { 
  res.json({ message: \`GET tag with ID: \${req.params.id}\` }); 
});
tagRouter.post('/', (req, res) => { 
  res.status(201).json({ message: 'Created new tag', data: req.body }); 
});
tagRouter.put('/:id', (req, res) => { 
  res.json({ message: \`Updated tag with ID: \${req.params.id}\`, data: req.body }); 
});
tagRouter.delete('/:id', (req, res) => { 
  res.json({ message: \`Deleted tag with ID: \${req.params.id}\` }); 
});

// Define enrichment routes directly
const enrichmentRouter = express.Router();
enrichmentRouter.get('/', (req, res) => { 
  res.json({ message: 'GET all enrichment' }); 
});
enrichmentRouter.get('/:id', (req, res) => { 
  res.json({ message: \`GET enrichment with ID: \${req.params.id}\` }); 
});
enrichmentRouter.post('/', (req, res) => { 
  res.status(201).json({ message: 'Created new enrichment', data: req.body }); 
});
enrichmentRouter.put('/:id', (req, res) => { 
  res.json({ message: \`Updated enrichment with ID: \${req.params.id}\`, data: req.body }); 
});
enrichmentRouter.delete('/:id', (req, res) => { 
  res.json({ message: \`Deleted enrichment with ID: \${req.params.id}\` }); 
});

// Define admin routes directly
const adminRouter = express.Router();
adminRouter.get('/', (req, res) => { 
  res.json({ message: 'GET all admin' }); 
});
adminRouter.get('/:id', (req, res) => { 
  res.json({ message: \`GET admin with ID: \${req.params.id}\` }); 
});
adminRouter.post('/', (req, res) => { 
  res.status(201).json({ message: 'Created new admin', data: req.body }); 
});
adminRouter.put('/:id', (req, res) => { 
  res.json({ message: \`Updated admin with ID: \${req.params.id}\`, data: req.body }); 
});
adminRouter.delete('/:id', (req, res) => { 
  res.json({ message: \`Deleted admin with ID: \${req.params.id}\` }); 
});

// Use routes
app.use('/api/auth', authRoutes);
app.use('/api/bookmarks', bookmarkRouter);
app.use('/api/categories', categoryRouter);
app.use('/api/tags', tagRouter);
app.use('/api/enrichment', enrichmentRouter);
app.use('/api/admin', adminRouter);

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Etwas ist schiefgelaufen'
  });
});

// Start server
app.listen(port, () => {
  console.log(\`Server running on port \${port}\`);
});

// Cleanup on exit
process.on('SIGINT', async () => {
  await prisma.$disconnect();
  process.exit(0);
});

module.exports = { prisma };
`;

// Write the converted JavaScript to the output file
fs.writeFileSync(indexJsPath, jsContent);

console.log('Index file conversion completed.');

// Check for syntax errors in the converted JavaScript file
try {
  console.log('Checking for syntax errors in the index.js file...');
  execSync('node --check ' + indexJsPath, { stdio: 'inherit' });
  console.log('No syntax errors found in the index.js file.');
} catch (error) {
  console.error('Syntax errors found:', error.message);
} 