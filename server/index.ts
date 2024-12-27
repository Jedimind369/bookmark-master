import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";

const app = express();

// Configure express with increased limits for large files
app.use((req, res, next) => {
  if (req.headers['content-type']?.includes('text/html')) {
    express.text({
      type: 'text/html',
      limit: '50mb',
      verify: (req, res, buf) => {
        if (buf.length > 50 * 1024 * 1024) { // 50MB limit
          throw new Error('File size too large. Maximum size is 50MB.');
        }
      }
    })(req, res, next);
  } else {
    next();
  }
});

app.use(express.json({
  limit: '50mb',
  verify: (req, res, buf) => {
    if (buf.length > 50 * 1024 * 1024) { // 50MB limit
      throw new Error('File size too large. Maximum size is 50MB.');
    }
  }
}));

app.use(express.urlencoded({ extended: false, limit: '50mb' }));

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
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      if (logLine.length > 80) {
        logLine = logLine.slice(0, 79) + "…";
      }

      log(logLine);
    }
  });

  next();
});

(async () => {
  const server = registerRoutes(app);

  // Error handling middleware
  app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
    const status = err.status || err.statusCode || 500;
    const message = err.message || "Internal Server Error";

    res.status(status).json({ message });
    throw err;
  });

  // importantly only setup vite in development and after
  // setting up all the other routes so the catch-all route
  // doesn't interfere with the other routes
  if (app.get("env") === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  // ALWAYS serve the app on port 5000
  // this serves both the API and the client
  const PORT = 5000;
  server.listen(PORT, "0.0.0.0", () => {
    log(`serving on port ${PORT}`);
  });
})();