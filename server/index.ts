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

// Performance optimization settings
const app = express();

// Configure express with optimized limits for files and disable x-powered-by
app.disable('x-powered-by');
app.set('trust proxy', 1);

// Setup monitoring first to track all requests
setupMonitoring(app);

// Optimize JSON parsing
app.use(express.json({
  limit: '2mb',
  verify: (req, res, buf) => {
    if (buf.length > 2 * 1024 * 1024) {
      throw new Error('File size too large. Maximum size is 2MB.');
    }
  }
}));

app.use(express.urlencoded({ extended: false, limit: '2mb' }));

// Error handling middleware for payload size
app.use((err: any, req: Request, res: Response, next: NextFunction) => {
  if (err instanceof Error && err.message.includes('File size too large')) {
    return res.status(413).json({ message: err.message });
  }
  if (err instanceof SyntaxError && err.message.includes('entity too large')) {
    return res.status(413).json({ message: 'File size too large. Maximum size is 2MB.' });
  }
  next(err);
});

// Memory-efficient logging middleware
const MAX_LOG_QUEUE = 100;
const logQueue: string[] = [];

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  const cleanup = () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        const responseStr = JSON.stringify(capturedJsonResponse);
        logLine += ` :: ${responseStr.length > 100 ? responseStr.slice(0, 97) + '...' : responseStr}`;
      }
      logQueue.push(logLine);
      if (logQueue.length > MAX_LOG_QUEUE) {
        logQueue.shift();
      }
      console.log(logLine);
    }
  };

  res.once("finish", cleanup);
  res.once("close", cleanup);
  next();
});

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
      // Start performance monitoring
      performanceMonitor.resetMetrics();
    });

    // Handle graceful shutdown
    process.on('SIGTERM', () => {
      console.log('SIGTERM received. Performing graceful shutdown...');
      server.close(() => {
        console.log('Server closed. Exiting process.');
        process.exit(0);
      });
    });
  } catch (error) {
    console.error("Failed to start server:", error);
    process.exit(1);
  }
})();