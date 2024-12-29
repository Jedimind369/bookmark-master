import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";

// Verify required environment variables
const requiredEnvVars = ['ANTHROPIC_API_KEY', 'DATABASE_URL'];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`${envVar} environment variable is not set`);
  }
}

const app = express();

// Configure express with optimized limits for files
app.use((req, res, next) => {
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
    return res.status(413).json({ message: 'File size too large. Maximum size is 50MB.' });
  }
  next(err);
});

// Memory-efficient logging middleware
const logQueue: string[] = [];
const MAX_LOG_QUEUE = 100;

app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;

  // Use a weak reference for response capture
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
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      if (logLine.length > 80) {
        logLine = logLine.slice(0, 79) + "…";
      }

      // Queue-based logging
      logQueue.push(logLine);
      if (logQueue.length > MAX_LOG_QUEUE) {
        logQueue.shift();  // Remove oldest log if queue is full
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
    }

    // Start the server
    const PORT = parseInt(process.env.PORT || "5000", 10);
    server.listen(PORT, "0.0.0.0", () => {
      log(`Server running at http://0.0.0.0:${PORT}`);
    });
  } catch (error) {
    console.error("Failed to start server:", error);
    process.exit(1);
  }
})();