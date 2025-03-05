#!/bin/sh
mkdir -p /app/src/server/dist
find /app/src/server -name "*.ts" | while read file; do
  outfile=$(echo $file | sed "s/\.ts$/.js/" | sed "s|/app/src/server/|/app/src/server/dist/|")
  mkdir -p $(dirname $outfile)
  cat $file | 
  sed -E "s/import ([a-zA-Z0-9_]+) from [\"']([^\"']+)[\"'];/const \1 = require(\"\2\");/g" | 
  sed -E "s/import \{ ([^}]+) \} from [\"']([^\"']+)[\"'];/const { \1 } = require(\"\2\");/g" | 
  sed -E "s/export const/const/g" | 
  sed -E "s/export default/module.exports =/g" | 
  sed -E "s/export \{/module.exports = {/g" | 
  sed -E "s/: [A-Za-z<>\[\]|&]+//g" | 
  sed -E "s/: any(\[\])?//g" | 
  sed -E "s/: (string|number|boolean|void|object|unknown|never|null|undefined)//g" | 
  sed -E "s/app\.use\(\(err: any, req: express\.Request, res: express\.Response, next: express\.NextFunction\) =>/app.use((err, req, res, next) =>/g" | 
  sed -E "s/app\.use\(\(err, req\.Request, res\.Response, next\.NextFunction\) =>/app.use((err, req, res, next) =>/g" | 
  sed -E "s/\(req: express\.Request, res: express\.Response(?:, next: express\.NextFunction)?\) =>/\(req, res, next\) =>/g" | 
  sed -E "s/\(_req: express\.Request, res: express\.Response(?:, next: express\.NextFunction)?\) =>/\(_req, res, next\) =>/g" | 
  sed -E "s/app\.use\(cors\(\{[^}]*\}\)\);/app.use(cors({\n  origin: ['http:\/\/localhost:3000', 'http:\/\/localhost:3001'],\n  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],\n  allowedHeaders: ['Content-Type', 'Authorization']\n}));/g" | 
  sed -E "s/res\.json\(\{ message\);/res.json({ message: 'Bookmark Master API' });/g" | 
  sed -E "s/res\.json\(\{ status\);/res.json({ status: 'ok' });/g" | 
  grep -v "^interface " | grep -v "^type " > $outfile
  echo "Processed $file -> $outfile"
done
find /app/src/server -name "*.json" | while read file; do
  outfile=$(echo $file | sed "s|/app/src/server/|/app/src/server/dist/|")
  mkdir -p $(dirname $outfile)
  cp $file $outfile
  echo "Copied $file -> $outfile"
done
