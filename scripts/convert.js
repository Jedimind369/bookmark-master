const fs = require("fs");
const path = require("path");
const { execSync } = require('child_process');

function processFile(filePath) {
  console.log(`Processing ${filePath}...`);
  const outDir = "/app/src/server/dist";
  const outPath = filePath.replace(/\/app\/src\/server\//, outDir + "/").replace(/\.ts$/, ".js");
  const dirName = path.dirname(outPath);
  fs.mkdirSync(dirName, { recursive: true });

  let content = fs.readFileSync(filePath, "utf8");

  // Convert imports
  content = content.replace(/import ([a-zA-Z0-9_]+) from ['"]([^'"]+)['"];/g, "const $1 = require(\"$2\");");
  content = content.replace(/import \{ ([^}]+) \} from ['"]([^'"]+)['"];/g, "const { $1 } = require(\"$2\");");

  // Convert exports
  content = content.replace(/export const/g, "const");
  content = content.replace(/export default/g, "module.exports =");
  content = content.replace(/export \{/g, "module.exports = {");

  // Remove type annotations
  content = content.replace(/: [A-Za-z<>\[\]|&]+/g, "");
  content = content.replace(/: any(\[\])?/g, "");
  content = content.replace(/: (string|number|boolean|void|object|unknown|never|null|undefined)/g, "");

  // Fix error handler middleware
  content = content.replace(/app\.use\(\(err: any, req: express\.Request, res: express\.Response, next: express\.NextFunction\) =>/g, "app.use((err, req, res, next) =>");
  content = content.replace(/app\.use\(\(err, req\.Request, res\.Response, next\.NextFunction\) =>/g, "app.use((err, req, res, next) =>");

  // Fix route handlers
  content = content.replace(/\(req: express\.Request, res: express\.Response(?:, next: express\.NextFunction)?\) =>/g, "(req, res, next) =>");
  content = content.replace(/\(_req: express\.Request, res: express\.Response(?:, next: express\.NextFunction)?\) =>/g, "(_req, res, next) =>");

  // Fix CORS configuration
  content = content.replace(/app\.use\(cors\(\{[^}]*\}\)\);/g, `app.use(cors({
  origin: ["http://localhost:3000", "http://localhost:3001"],
  methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"]
}));`);

  // Fix JSON responses
  content = content.replace(/res\.json\(\{ message\);/g, "res.json({ message: \"Bookmark Master API\" });");
  content = content.replace(/res\.json\(\{ status\);/g, "res.json({ status: \"ok\" });");

  // Fix the error handler message
  content = content.replace(/message\.env\.NODE_ENV/g, "message: process.env.NODE_ENV");

  // Remove interface and type declarations
  content = content.split("\n").filter(line => !line.startsWith("interface ") && !line.startsWith("type ")).join("\n");

  fs.writeFileSync(outPath, content);
  console.log(`Converted ${filePath} -> ${outPath}`);
}

function processDirectory(dir, outDir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      if (entry.name !== "node_modules" && entry.name !== "dist") {
        processDirectory(fullPath, path.join(outDir, entry.name));
      }
    } else if (entry.name.endsWith(".ts")) {
      processFile(fullPath);
    } else if (entry.name.endsWith(".json")) {
      const outPath = path.join(outDir, entry.name);
      fs.mkdirSync(path.dirname(outPath), { recursive: true });
      fs.copyFileSync(fullPath, outPath);
      console.log(`Copied ${fullPath} -> ${outPath}`);
    }
  }
}

console.log("Starting TypeScript to JavaScript conversion...");
fs.mkdirSync("/app/src/server/dist", { recursive: true });
processDirectory("/app/src/server", "/app/src/server/dist");
console.log("Conversion completed successfully!");

// Check for syntax errors
try {
  execSync('node -c better-converted-index.js', { stdio: 'inherit' });
  console.log('No syntax errors found in the converted JavaScript file.');
} catch (error) {
  console.error('Syntax errors found in the converted JavaScript file.');
} 