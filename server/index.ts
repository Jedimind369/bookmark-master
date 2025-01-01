import 'reflect-metadata';
import express from 'express';
import { container } from './container';
import type { IBookmarkService } from './interfaces/services';
import { registerRoutes } from './routes';
import { performanceMonitor } from './utils/monitoring';
import { setupMonitoring } from './services/monitoringService';
import { logger } from './utils/logger';

// Initialize dependency injection
const bookmarkService = container.resolve<IBookmarkService>('IBookmarkService');

// Verify required environment variables
const requiredEnvVars = ['ANTHROPIC_API_KEY', 'DATABASE_URL'];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`${envVar} environment variable is not set`);
  }
}

const app = express();

// Configure express with optimized limits
app.disable('x-powered-by');
app.set('trust proxy', 1);

// Setup monitoring first to track all requests
setupMonitoring(app);

// Core middleware with size limits
app.use(express.json({
  limit: '2mb',
  verify: (req, res, buf) => {
    if (buf.length > 2 * 1024 * 1024) {
      throw new Error('File size too large. Maximum size is 2MB.');
    }
  }
}));

app.use(express.urlencoded({ extended: false, limit: '2mb' }));

// Health check endpoint
app.get('/health', async (_req, res) => {
  try {
    // Test bookmark service
    const testBookmark = await bookmarkService.enrich({
      url: 'https://example.com',
      title: 'Health Check'
    });
    
    res.json({ 
      status: 'healthy',
      timestamp: new Date().toISOString(),
      services: {
        bookmark: testBookmark ? 'ok' : 'error'
      }
    });
  } catch (error) {
    logger.error('Health check failed:', { error: error instanceof Error ? error.message : 'Unknown error' });
    res.status(500).json({ 
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// Initialize routes
(async () => {
  try {
    logger.info("Starting server initialization...");
    const server = registerRoutes(app);

    // Global error handling middleware
    app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
      logger.error("Server error:", { 
        message: err.message || "Internal Server Error",
        status: err.status || err.statusCode || 500
      });
      const status = err.status || err.statusCode || 500;
      const message = err.message || "Internal Server Error";
      res.status(status).json({ message });
    });

    // Start the server
    const PORT = parseInt(process.env.PORT || "5000", 10);
    server.listen(PORT, "0.0.0.0", () => {
      logger.info(`Server running at http://0.0.0.0:${PORT}`);
      performanceMonitor.resetMetrics();
    });

  } catch (error) {
    logger.error("Failed to start server:", { error: error instanceof Error ? error.message : 'Unknown error' });
    process.exit(1);
  }
})();
