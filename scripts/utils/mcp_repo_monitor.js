#!/usr/bin/env node

/**
 * MCP Repository Monitor
 * 
 * Dieses Skript überwacht das Repository über den MCP-Server und
 * führt bei wichtigen Änderungen automatisch eine Synchronisation durch.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const https = require('https');

// Konfiguration
const config = {
  owner: 'Jedimind369',
  repo: 'bookmark-master',
  branch: 'features/hybrid-optimization',
  checkInterval: 15 * 60 * 1000, // 15 Minuten in Millisekunden
  importantDirectories: ['scripts/ai', 'tests', 'src/core', 'config'],
  logFile: path.join(__dirname, '../../logs/mcp_monitor.log')
};

// Stelle sicher, dass das Log-Verzeichnis existiert
const logDir = path.dirname(config.logFile);
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

// Logging-Funktion
function log(message) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}`;
  console.log(logMessage);
  fs.appendFileSync(config.logFile, logMessage + '\n');
}

// Funktion zum Abrufen der neuesten Commits
function getLatestCommits() {
  try {
    log('Rufe neueste Commits ab...');
    
    const options = {
      hostname: 'api.github.com',
      path: `/repos/${config.owner}/${config.repo}/commits?sha=${config.branch}`,
      method: 'GET',
      headers: {
        'User-Agent': 'MCP-Repository-Monitor',
        'Accept': 'application/vnd.github.v3+json'
      }
    };
    
    return new Promise((resolve, reject) => {
      const req = https.request(options, (res) => {
        let data = '';
        
        res.on('data', (chunk) => {
          data += chunk;
        });
        
        res.on('end', () => {
          if (res.statusCode === 200) {
            resolve(JSON.parse(data));
          } else {
            reject(new Error(`Status Code: ${res.statusCode}, Nachricht: ${data}`));
          }
        });
      });
      
      req.on('error', (error) => {
        reject(error);
      });
      
      req.end();
    });
  } catch (error) {
    log(`Fehler beim Abrufen der Commits: ${error.message}`);
    return [];
  }
}

// Funktion zum Überprüfen, ob wichtige Dateien geändert wurden
function checkForImportantChanges(commits) {
  try {
    if (!commits || commits.length === 0) {
      return false;
    }
    
    // Prüfe nur den neuesten Commit
    const latestCommit = commits[0];
    log(`Prüfe Commit: ${latestCommit.sha} - ${latestCommit.commit.message}`);
    
    // Rufe die geänderten Dateien für diesen Commit ab
    const options = {
      hostname: 'api.github.com',
      path: `/repos/${config.owner}/${config.repo}/commits/${latestCommit.sha}`,
      method: 'GET',
      headers: {
        'User-Agent': 'MCP-Repository-Monitor',
        'Accept': 'application/vnd.github.v3+json'
      }
    };
    
    return new Promise((resolve, reject) => {
      const req = https.request(options, (res) => {
        let data = '';
        
        res.on('data', (chunk) => {
          data += chunk;
        });
        
        res.on('end', () => {
          if (res.statusCode === 200) {
            const commitData = JSON.parse(data);
            const files = commitData.files || [];
            
            // Prüfe, ob wichtige Verzeichnisse betroffen sind
            const importantChanges = files.some(file => {
              return config.importantDirectories.some(dir => 
                file.filename.startsWith(dir)
              );
            });
            
            if (importantChanges) {
              log('Wichtige Änderungen gefunden!');
            } else {
              log('Keine wichtigen Änderungen gefunden.');
            }
            
            resolve(importantChanges);
          } else {
            reject(new Error(`Status Code: ${res.statusCode}, Nachricht: ${data}`));
          }
        });
      });
      
      req.on('error', (error) => {
        reject(error);
      });
      
      req.end();
    });
  } catch (error) {
    log(`Fehler beim Prüfen auf wichtige Änderungen: ${error.message}`);
    return false;
  }
}

// Funktion zum Synchronisieren des Repositories
function syncRepository() {
  try {
    log('Führe Repository-Synchronisation durch...');
    const result = execSync('bash scripts/utils/repo_sync.sh').toString();
    log(result);
    return true;
  } catch (error) {
    log(`Fehler bei der Repository-Synchronisation: ${error.message}`);
    return false;
  }
}

// Hauptfunktion
async function monitorRepository() {
  try {
    log('Starte Repository-Überwachung...');
    
    // Rufe die neuesten Commits ab
    const commits = await getLatestCommits();
    
    // Prüfe, ob wichtige Änderungen vorliegen
    const hasImportantChanges = await checkForImportantChanges(commits);
    
    // Wenn wichtige Änderungen gefunden wurden, synchronisiere das Repository
    if (hasImportantChanges) {
      syncRepository();
    }
    
    // Plane die nächste Überprüfung
    log(`Nächste Überprüfung in ${config.checkInterval / 60000} Minuten...`);
    setTimeout(monitorRepository, config.checkInterval);
  } catch (error) {
    log(`Fehler bei der Repository-Überwachung: ${error.message}`);
    log(`Versuche erneut in ${config.checkInterval / 60000} Minuten...`);
    setTimeout(monitorRepository, config.checkInterval);
  }
}

// Starte die Überwachung
log('MCP Repository Monitor gestartet');
monitorRepository(); 