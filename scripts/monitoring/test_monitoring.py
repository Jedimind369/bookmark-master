#!/usr/bin/env python3

"""
test_monitoring.py

Testskript für die API-Monitoring-Funktionalität.
"""

import os
import asyncio
import argparse
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Union
import json

# Füge den Projektpfad zum Systempfad hinzu
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.monitoring import APIMonitor
from scripts.ai.api_client import ModelAPIClient

async def test_multiple_api_calls(num_calls=5, model="qwq", budget_limit=10.0):
    """
    Führt mehrere API-Aufrufe durch, um die Überwachungsfunktionalität zu testen.
    
    Args:
        num_calls: Anzahl der durchzuführenden API-Aufrufe
        model: Zu verwendendes Modell (qwq, claude_sonnet, deepseek_r1, gpt4o_mini)
        budget_limit: Budgetlimit für den Test
    """
    print(f"=== Starte Test mit {num_calls} Aufrufen für Modell {model} ===")
    
    # Initialisiere den API-Client mit Monitoring
    client = ModelAPIClient(budget_limit=budget_limit)
    
    # Test-Prompts
    prompts = [
        "Was ist ein Bookmark-Management-System?",
        "Erkläre die Vorteile einer semantischen Suche.",
        "Wie organisiert man Lesezeichen effizient?",
        "Was sind die besten Praktiken für die Datenspeicherung?",
        "Wie kann KI bei der Kategorisierung von Lesezeichen helfen?"
    ]
    
    total_cost = 0.0
    successful_calls = 0
    
    for i in range(num_calls):
        prompt = prompts[i % len(prompts)]
        try:
            print(f"\nAPI-Aufruf {i+1}/{num_calls}: {model}")
            result = await client.call_model(
                model_id=model, 
                prompt=prompt, 
                max_tokens=50,  # Kleine Antwortlänge für den Test
                use_cache=False  # Cache deaktivieren, um jeden Aufruf zu tracken
            )
            
            if "error" not in result:
                successful_calls += 1
                cost = result.get("cost", 0)
                total_cost += cost
                print(f"Antwort: {result['response'][:50]}...")
                print(f"Kosten: ${cost:.6f}")
            else:
                print(f"Fehler: {result['error']}")
        
        except Exception as e:
            print(f"Fehler beim API-Aufruf: {str(e)}")
    
    print("\n=== Testergebnisse ===")
    print(f"Erfolgreiche API-Aufrufe: {successful_calls}/{num_calls}")
    print(f"Gesamtkosten: ${total_cost:.6f}")
    
    # Nutzungsstatistik anzeigen
    client.api_monitor.show_usage(detailed=True)
    
    return total_cost

async def simulate_api_usage(budget=5.0, target_percentage=0.8):
    """
    Simuliert API-Nutzung bis zu einem bestimmten Prozentsatz des Budgets.
    
    Args:
        budget: Budgetlimit für die Simulation
        target_percentage: Ziel-Prozentsatz des Budgets (0-1)
    """
    print(f"=== Simuliere API-Nutzung bis zu {target_percentage*100}% des Budgets (${budget:.2f}) ===")
    
    # Initialisiere den API-Monitor
    monitor = APIMonitor(budget_limit=budget)
    
    # Simulierte API-Modelle mit ihren Kosten
    models = {
        "qwq": {"min_cost": 0.0001, "max_cost": 0.001, "tokens_min": 100, "tokens_max": 500},
        "claude_sonnet": {"min_cost": 0.005, "max_cost": 0.02, "tokens_min": 100, "tokens_max": 300},
        "deepseek_r1": {"min_cost": 0.0003, "max_cost": 0.003, "tokens_min": 100, "tokens_max": 400},
        "gpt4o_mini": {"min_cost": 0.0002, "max_cost": 0.002, "tokens_min": 100, "tokens_max": 400}
    }
    
    # Simulierte Aufgaben
    tasks = ["scraping", "analysis", "categorization", "recommendation", "search"]
    
    # Simuliere API-Aufrufe
    total_cost = 0
    target_cost = budget * target_percentage
    call_count = 0
    
    while total_cost < target_cost:
        # Wähle ein zufälliges Modell
        model = random.choice(list(models.keys()))
        model_info = models[model]
        
        # Simuliere Kosten und Tokens
        cost = random.uniform(model_info["min_cost"], model_info["max_cost"])
        tokens_in = random.randint(model_info["tokens_min"], model_info["tokens_max"])
        tokens_out = random.randint(50, 200)
        task = random.choice(tasks)
        
        # Zeichne API-Aufruf auf
        monitor.record_api_call(
            model=model,
            cost=cost,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            task=f"bookmark-master-{task}"
        )
        
        total_cost += cost
        call_count += 1
        
        if call_count % 10 == 0:
            print(f"Simuliere API-Aufrufe: {call_count} abgeschlossen, Kosten: ${total_cost:.4f}")
    
    print(f"\n=== Simulation abgeschlossen ===")
    print(f"Simulierte API-Aufrufe: {call_count}")
    print(f"Gesamtkosten: ${total_cost:.4f} von Budget ${budget:.2f} ({total_cost/budget*100:.1f}%)")
    
    # Zeige detaillierte Nutzungsstatistik
    monitor.show_usage(detailed=True)

async def test_backup_functionality(days_to_simulate=7):
    """
    Testet die Backup-Funktionalität, indem mehrere tägliche Backups simuliert werden.
    
    Args:
        days_to_simulate: Anzahl der zu simulierenden Tage.
    """
    print(f"\n{'='*20} BACKUP-FUNKTIONALITÄT TESTEN {'='*20}")
    
    # Monitor initialisieren
    monitor = APIMonitor(budget_limit=10.0)
    
    # Aktuelle Nutzungsdaten speichern
    original_data = monitor.data.copy() if hasattr(monitor, 'data') else None
    
    # Simuliere Backups für mehrere Tage
    print(f"Simuliere {days_to_simulate} Tage mit Backups...")
    
    for day in range(days_to_simulate):
        # Simuliere einen anderen Tag
        simulated_date = (datetime.now() - timedelta(days=days_to_simulate-day)).date().isoformat()
        
        # Füge einige simulierte API-Aufrufe hinzu
        num_calls = random.randint(5, 15)
        daily_cost = 0.0
        
        for _ in range(num_calls):
            model = random.choice(["qwq", "claude_sonnet", "deepseek_r1", "gpt4o_mini"])
            cost = random.uniform(0.001, 0.1)
            daily_cost += cost
            
            # Aufzeichnen des simulierten API-Aufrufs mit dem simulierten Datum
            monitor.data['api_calls'].append({
                "timestamp": f"{simulated_date}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}",
                "model": model,
                "tokens_in": random.randint(50, 500),
                "tokens_out": random.randint(20, 300),
                "cost": cost,
                "task": "test-backup-simulation"
            })
            
            # Aktualisiere die Modellstatistiken
            if model not in monitor.data['models']:
                monitor.data['models'][model] = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0}
            monitor.data['models'][model]['calls'] += 1
            monitor.data['models'][model]['tokens_in'] += monitor.data['api_calls'][-1]['tokens_in']
            monitor.data['models'][model]['tokens_out'] += monitor.data['api_calls'][-1]['tokens_out']
            monitor.data['models'][model]['cost'] += cost
            
            # Aktualisiere die Aufgabenstatistiken
            task = "test-backup-simulation"
            if task not in monitor.data['tasks']:
                monitor.data['tasks'][task] = {"calls": 0, "cost": 0.0}
            monitor.data['tasks'][task]['calls'] += 1
            monitor.data['tasks'][task]['cost'] += cost
        
        # Aktualisiere die Gesamtkosten
        monitor.data['total_cost'] += daily_cost
        print(f"Tag {simulated_date}: {num_calls} API-Aufrufe, ${daily_cost:.2f} Kosten")
        
        # Für den ersten Tag erstellen wir ein vollständiges Backup, für die anderen inkrementelle
        backup_type = "full" if day == 0 else "incremental"
        
        # Speichere die simulierten Daten
        with open(monitor.usage_file, 'w') as f:
            json.dump(monitor.data, f, indent=2)
        
        # Erstelle ein künstliches Backup
        if backup_type == "full":
            # Vollständiges Backup
            backup_success = monitor._create_full_backup()
            backup_file_pattern = f"api_usage_backup_{simulated_date}_full.json"
        else:
            # Inkrementelles Backup
            backup_success = monitor._create_backup(incremental=True)
            backup_file_pattern = f"api_usage_backup_{simulated_date}_incremental.json"
        
        if backup_success:
            print(f"{backup_type.capitalize()} Backup für {simulated_date} erstellt")
            
            # Validiere das Backup
            backup_files = list(monitor.backup_dir.glob(f"*{simulated_date}*.json"))
            if backup_files:
                backup_file = backup_files[0]
                if monitor._verify_backup_integrity(backup_file):
                    print(f"Integritätsprüfung für {backup_file.name} erfolgreich")
                else:
                    print(f"Integritätsprüfung für {backup_file.name} fehlgeschlagen!")
            
            # Aktualisiere Backup-Metadaten
            metadata = monitor._load_backup_metadata()
            
            if 'backups' not in metadata:
                metadata['backups'] = []
                
            metadata['last_backup_date'] = simulated_date
            metadata['backup_count'] = metadata.get('backup_count', 0) + 1
            
            # Füge Backup-Infos hinzu
            backup_file = list(monitor.backup_dir.glob(f"*{simulated_date}*.json"))[0]
            
            base_backup = None
            if backup_type == "incremental" and metadata.get('backups'):
                # Finde das letzte vollständige Backup
                for b in reversed(metadata['backups']):
                    if b.get('type') == 'full':
                        base_backup = b['file']
                        break
            
            metadata['backups'].append({
                'date': simulated_date,
                'file': backup_file.name,
                'type': backup_type,
                'base_backup': base_backup,
                'size': os.path.getsize(backup_file),
                'total_cost': monitor.data['total_cost']
            })
            
            monitor._save_backup_metadata(metadata)
        else:
            print(f"Fehler beim Erstellen des Backups für {simulated_date}")
    
    # Zeige die verfügbaren Backups an
    print("\nVerfügbare Backups:")
    backups = monitor.list_available_backups()
    for backup in backups:
        backup_type = backup.get('type', 'unbekannt')
        base_info = f" (basiert auf {backup.get('base_backup')})" if backup.get('base_backup') else ""
        print(f"Datum: {backup['date']}, Typ: {backup_type}{base_info}, "
              f"Größe: {backup['size']} bytes, Gesamtkosten: ${backup['total_cost']:.2f}")
    
    # Teste die Wiederherstellung aus einem zufälligen Backup
    if backups:
        # Wähle ein zufälliges Backup
        random_backup = random.choice(backups)
        print(f"\nWiederherstellung aus {random_backup.get('type', 'unbekannt')} Backup vom {random_backup['date']} testen...")
        
        # Speichere den aktuellen Zustand, um Vergleiche zu ermöglichen
        current_total_cost = monitor.data['total_cost']
        
        # Führe die Wiederherstellung durch
        success = monitor.restore_from_backup(specific_date=random_backup['date'])
        
        if success:
            restored_total_cost = monitor.data['total_cost']
            print(f"Wiederherstellung erfolgreich!")
            print(f"Kosten vor Wiederherstellung: ${current_total_cost:.2f}")
            print(f"Kosten nach Wiederherstellung: ${restored_total_cost:.2f}")
        else:
            print("Wiederherstellung fehlgeschlagen!")
    
    # Teste auch gezielt die Wiederherstellung aus einem inkrementellen Backup
    incremental_backups = [b for b in backups if b.get('type') == 'incremental']
    if incremental_backups:
        inc_backup = incremental_backups[-1]  # Nehme das neueste inkrementelle Backup
        print(f"\nWiederherstellung speziell aus inkrementellen Backup vom {inc_backup['date']} testen...")
        
        # Führe die Wiederherstellung durch
        success = monitor.restore_from_backup(specific_date=inc_backup['date'])
        
        if success:
            print(f"Wiederherstellung aus inkrementellem Backup erfolgreich!")
        else:
            print("Wiederherstellung aus inkrementellem Backup fehlgeschlagen!")
    
    # Teste die Backup-Rotation
    if len(backups) > monitor.max_daily_backups:
        print(f"\nTeste Backup-Rotation (max. {monitor.max_daily_backups} Backups)...")
        monitor._cleanup_old_backups(monitor._load_backup_metadata())
        
        # Zeige die verbleibenden Backups nach der Rotation
        remaining_backups = monitor.list_available_backups()
        print(f"Nach Rotation: {len(remaining_backups)} Backups übrig")
        
        if len(remaining_backups) <= monitor.max_daily_backups:
            print("Backup-Rotation erfolgreich!")
        else:
            print(f"Backup-Rotation fehlgeschlagen: {len(remaining_backups)} > {monitor.max_daily_backups}")
    
    # Stelle die ursprünglichen Daten wieder her, wenn verfügbar
    if original_data:
        monitor.data = original_data
        monitor._save_data()
        print("\nUrsprüngliche Daten wiederhergestellt.")
    
    return monitor

async def main():
    parser = argparse.ArgumentParser(description="Test API-Monitoring-Funktionalität")
    parser.add_argument("--real", action="store_true", help="Echte API-Aufrufe durchführen")
    parser.add_argument("--simulate", action="store_true", help="API-Nutzung simulieren")
    parser.add_argument("--backup", action="store_true", help="Teste die Backup-Funktionalität")
    parser.add_argument("--calls", type=int, default=5, help="Anzahl der API-Aufrufe")
    parser.add_argument("--model", type=str, default="qwq", help="Zu verwendendes Modell")
    parser.add_argument("--budget", type=float, default=10.0, help="Budgetlimit für den Test")
    parser.add_argument("--target", type=float, default=0.8, help="Ziel-Prozentsatz des Budgets (0-1)")
    parser.add_argument("--days", type=int, default=7, help="Anzahl der zu simulierenden Tage für Backup-Test")
    args = parser.parse_args()
    
    if args.backup:
        await test_backup_functionality(days_to_simulate=args.days)
    elif args.real:
        await test_multiple_api_calls(num_calls=args.calls, model=args.model, budget_limit=args.budget)
    elif args.simulate:
        await simulate_api_usage(budget=args.budget, target_percentage=args.target)
    else:
        print("Wähle entweder --real, --simulate oder --backup. Benutze --help für weitere Informationen.")

if __name__ == "__main__":
    asyncio.run(main()) 