const express = require("express");
const cors = require("cors");
const dotenv = require("dotenv");
const { PrismaClient } = require("@prisma/client");

// Lade Umgebungsvariablen
dotenv.config();

// Debug-Ausgabe der Umgebungsvariablen
console.log("index.ts variables after dotenv.config():");
console.log(`USE_DIRECT_ZYTE_API=${process.env.USE_DIRECT_ZYTE_API}`);
console.log(`ZYTE_API_KEY=${process.env.ZYTE_API_KEY ? '(set)' : '(not set)'}`);
console.log(`NODE_ENV=${process.env.NODE_ENV}`);
console.log(`PORT=${process.env.PORT}`);

// Setze die Variable explizit, wenn sie über die Kommandozeile übergeben wurde
if (process.env.USE_DIRECT_ZYTE_API === 'true') {
  console.log("index.ts direct Zyte API as specified in environment variables");
}

// Initialisiere Express-App
const app = express();
const port = process.env.PORT ? parseInt(process.env.PORT, 10) : 8000;

// Initialisiere Prisma-Client
const prisma = new PrismaClient();

// Middleware
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:3001'],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(express.json());

// Basis-Route
app.get('/', (req, res) => {
  res.json({ message: 'Bookmark Master API' });
});

// Health check endpoint
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok' });
});

// API-Routes importieren
const authRoutes = require("./routes/auth");
const bookmarkRoutes = require("./routes/bookmark");
const categoryRoutes = require("./routes/category");
const tagRoutes = require("./routes/tag");
const enrichmentRoutes = require("./routes/enrichment");
const adminRoutes = require("./routes/admin");

app.use('/api/auth', authRoutes);
app.use('/api/bookmarks', bookmarkRoutes);
app.use('/api/categories', categoryRoutes);
app.use('/api/tags', tagRoutes);
app.use('/api/enrichment', enrichmentRoutes);
app.use('/api/admin', adminRoutes);

// Error-Handling Middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Internal Server Error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Etwas ist schiefgelaufen'
  });
});

// Starte Server
app.listen(port, () => {
  console.log(`Server läuft auf Port ${port}`);
});

// Cleanup bei Beendigung
process.on('SIGINT', async () => {
  await prisma.$disconnect();
  process.exit(0);
}); 