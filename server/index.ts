
import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { performanceMonitor } from "./utils/monitoring";
import { setupMonitoring } from "./services/monitoringService";

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
app.get('/health', (_req: Request, res: Response) => {
  res.json({ 
    status: 'healthy',
    timestamp: new Date().toISOString()
  });
});

// Initialize routes
(async () => {
  try {
    console.log("Starting server initialization...");
    const server = registerRoutes(app);

    // Global error handling middleware
    app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
      console.error("Server error:", err);
      const status = err.status || err.statusCode || 500;
      const message = err.message || "Internal Server Error";
      res.status(status).json({ message });
    });

    // Start the server
    const PORT = parseInt(process.env.PORT || "5000", 10);
    server.listen(PORT, "0.0.0.0", () => {
      console.log(`Server running at http://0.0.0.0:${PORT}`);
      performanceMonitor.resetMetrics();
    });

  } catch (error) {
    console.error("Failed to start server:", error);
    process.exit(1);
  }
})();
