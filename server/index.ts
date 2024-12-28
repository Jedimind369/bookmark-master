import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";
import { testDatabaseConnection } from "@db";

// Verify required environment variables
const requiredEnvVars = ['ANTHROPIC_API_KEY', 'DATABASE_URL'];
for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    console.error(`Missing required environment variable: ${envVar}`);
    process.exit(1);
  }
}

const app = express();

// Configure express with increased limits for large files
app.use(express.json({
  limit: '50mb',
  verify: (req, res, buf) => {
    if (buf.length > 50 * 1024 * 1024) { // 50MB limit
      throw new Error('File size too large. Maximum size is 50MB.');
    }
  }
}));

app.use(express.urlencoded({ extended: false, limit: '50mb' }));

// Logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        const responseSummary = JSON.stringify(capturedJsonResponse);
        logLine += ` :: ${responseSummary.length > 100 ? responseSummary.slice(0, 97) + '...' : responseSummary}`;
      }
      log(logLine);
    }
  });

  next();
});

// Global error handling middleware with better logging
app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
  console.error("Server error:", {
    message: err.message,
    stack: err.stack,
    code: err.code,
    status: err.status || err.statusCode
  });

  const status = err.status || err.statusCode || 500;
  const message = err.message || "Internal Server Error";

  res.status(status).json({ 
    message,
    error: app.get('env') === 'development' ? err.stack : undefined
  });
});

// Server initialization with proper error handling
(async () => {
  try {
    console.log("Starting server initialization...");

    // Test database connection first
    const dbConnected = await testDatabaseConnection();
    if (!dbConnected) {
      throw new Error("Failed to connect to database");
    }
    console.log("Database connection successful");

    const server = registerRoutes(app);

    // Setup development environment
    if (app.get("env") === "development") {
      await setupVite(app, server);
    } else {
      serveStatic(app);
    }

    // Try multiple ports if default port is in use
    const tryPort = (port: number): Promise<void> => {
      return new Promise((resolve, reject) => {
        server.listen(port, "0.0.0.0")
          .once('listening', () => {
            log(`Server running at http://0.0.0.0:${port}`);
            resolve();
          })
          .once('error', (err: NodeJS.ErrnoException) => {
            if (err.code === 'EADDRINUSE') {
              console.log(`Port ${port} in use, trying next port...`);
              tryPort(port + 1).then(resolve).catch(reject);
            } else {
              reject(err);
            }
          });
      });
    };

    // Start with port 5000 and try subsequent ports if needed
    await tryPort(5000);

  } catch (error) {
    console.error("Failed to start server:", error);
    process.exit(1);
  }
})();