import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";
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

// Configure express with optimized limits for files
app.use((req, res, next) => {
  // Set response timeout
  res.setTimeout(30000, () => {
    res.status(503).json({ message: 'Request timeout' });
  });

  if (req.headers['content-type']?.includes('text/html')) {
    express.text({
      type: 'text/html',
      limit: '5mb',
      verify: (req, res, buf) => {
        if (buf.length > 5 * 1024 * 1024) {
          throw new Error('File size too large. Maximum size is 5MB.');
        }
      }
    })(req, res, next);
  } else {
    next();
  }
});

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

// Memory-efficient logging middleware with circular buffer
const logQueue: string[] = [];
const MAX_LOG_QUEUE = 100;

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;

  // Use WeakRef for response capture to allow garbage collection
  let capturedJsonResponse: Record<string, any> | undefined = undefined;
  const originalResJson = res.json;

  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  const cleanup = () => {
    // Clean up response capture
    capturedJsonResponse = undefined;

    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;

      // Truncate response logging to prevent memory leaks
      if (capturedJsonResponse) {
        const responseStr = JSON.stringify(capturedJsonResponse);
        logLine += ` :: ${responseStr.length > 100 ? responseStr.slice(0, 97) + '...' : responseStr}`;
      }

      // Queue-based logging with size limit
      logQueue.push(logLine);
      if (logQueue.length > MAX_LOG_QUEUE) {
        logQueue.shift();
      }
      log(logLine);
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

    // Setup development environment
    if (app.get("env") === "development") {
      await setupVite(app, server);
    } else {
      serveStatic(app);

      // Enable garbage collection hints in production
      if (global.gc) {
        setInterval(() => {
          try {
            global.gc();
          } catch (error) {
            console.error('Failed to run garbage collection:', error);
          }
        }, 30000); // Run every 30 seconds
      }
    }

    // Start the server
    const PORT = parseInt(process.env.PORT || "5000", 10);
    server.listen(PORT, "0.0.0.0", () => {
      log(`Server running at http://0.0.0.0:${PORT}`);

      // Start performance monitoring
      performanceMonitor.resetMetrics();
    });
  } catch (error) {
    console.error("Failed to start server:", error);
    process.exit(1);
  }
})();

// Handle graceful shutdown
process.on('SIGTERM', () => {
  log('SIGTERM received. Performing graceful shutdown...');
  server.close(() => {
    log('Server closed. Exiting process.');
    process.exit(0);
  });
});