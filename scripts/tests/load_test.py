#!/usr/bin/env python3
"""
Last-Test-Skript für den Bookmark-Processor
Generiert eine große Anzahl von Bookmark-Anfragen, um die Leistung und Stabilität zu testen
"""

import argparse
import concurrent.futures
import json
import random
import time
import string
import requests
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from pathlib import Path


def generate_random_url():
    """Generiert eine zufällige URL"""
    domains = ['example.com', 'test.org', 'bookmark.io', 'sample.net', 'demo.dev']
    paths = ['', 'about', 'products', 'services', 'blog', 'contact']
    domain = random.choice(domains)
    path = random.choice(paths)
    return f"https://www.{domain}/{path}"


def generate_random_title(length=8):
    """Generiert einen zufälligen Titel"""
    words = ['Bookmark', 'Test', 'Demo', 'Sample', 'Example', 'Page', 'Website', 'Link', 'Resource']
    return ' '.join(random.sample(words, min(length, len(words))))


def generate_test_bookmarks(count):
    """Generiert eine Liste von Test-Lesezeichen"""
    bookmarks = []
    for i in range(count):
        bookmark = {
            'url': generate_random_url(),
            'title': generate_random_title(),
            'description': f'Automatisch generiertes Test-Lesezeichen {i}',
            'tags': random.sample(['test', 'demo', 'sample', 'bookmark', 'generated'], 
                                random.randint(1, 3)),
            'created_at': datetime.now().isoformat()
        }
        bookmarks.append(bookmark)
    return bookmarks


def write_bookmarks_to_file(bookmarks, file_path):
    """Schreibt Lesezeichen in eine JSON-Datei"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(bookmarks, f, indent=2)
    return file_path


def process_bookmark_file(processor_url, file_path, max_workers, min_chunk_size, max_chunk_size, memory_target):
    """Verarbeitet eine Lesezeichen-Datei über die Processor API"""
    url = f"{processor_url}/process/json"
    payload = {
        'file_path': str(file_path),
        'max_workers': max_workers,
        'min_chunk_size': min_chunk_size,
        'max_chunk_size': max_chunk_size,
        'memory_target': memory_target
    }
    start_time = time.time()
    response = requests.post(url, json=payload)
    end_time = time.time()
    
    if response.status_code == 200:
        result = response.json()
        result['duration'] = end_time - start_time
        return result
    else:
        raise Exception(f"Fehler bei der Verarbeitung: {response.status_code}, {response.text}")


def process_bookmark_urls(processor_url, urls, max_workers, min_chunk_size, max_chunk_size, memory_target):
    """Verarbeitet eine Liste von URLs über die Processor API"""
    url = f"{processor_url}/process/urls"
    payload = {
        'urls': urls,
        'max_workers': max_workers,
        'min_chunk_size': min_chunk_size,
        'max_chunk_size': max_chunk_size,
        'memory_target': memory_target
    }
    start_time = time.time()
    response = requests.post(url, json=payload)
    end_time = time.time()
    
    if response.status_code == 200:
        result = response.json()
        result['duration'] = end_time - start_time
        return result
    else:
        raise Exception(f"Fehler bei der Verarbeitung: {response.status_code}, {response.text}")


def get_processor_stats(processor_url):
    """Ruft die aktuellen Processor-Statistiken ab"""
    url = f"{processor_url}/stats"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Fehler beim Abrufen der Statistiken: {response.status_code}, {response.text}")


def run_serial_test(processor_url, num_bookmarks, num_files, max_workers, min_chunk_size, max_chunk_size, memory_target):
    """Führt sequenzielle Tests durch"""
    results = []
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    
    print(f"Serieller Test mit {num_files} Dateien, jeweils {num_bookmarks} Lesezeichen...")
    
    for i in range(num_files):
        # Generiere Lesezeichen
        bookmarks = generate_test_bookmarks(num_bookmarks)
        file_path = temp_dir / f"bookmarks_test_{i}.json"
        write_bookmarks_to_file(bookmarks, file_path)
        
        # Verarbeite Datei
        print(f"Verarbeite Datei {i+1}/{num_files}...")
        try:
            result = process_bookmark_file(processor_url, file_path, max_workers, min_chunk_size, max_chunk_size, memory_target)
            results.append(result)
            print(f"  Datei {i+1} verarbeitet: {result['items_processed']} Lesezeichen in {result['duration']:.2f} Sekunden")
        except Exception as e:
            print(f"  Fehler bei Datei {i+1}: {str(e)}")
    
    return results


def run_parallel_test(processor_url, num_bookmarks, num_files, max_concurrent, max_workers, min_chunk_size, max_chunk_size, memory_target):
    """Führt parallele Tests durch"""
    results = []
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    
    # Generiere alle Testdateien
    files = []
    for i in range(num_files):
        bookmarks = generate_test_bookmarks(num_bookmarks)
        file_path = temp_dir / f"bookmarks_parallel_{i}.json"
        write_bookmarks_to_file(bookmarks, file_path)
        files.append(file_path)
    
    print(f"Paralleler Test mit {num_files} Dateien, {max_concurrent} gleichzeitig...")
    
    # Funktion für den Worker-Pool
    def process_file(file_path):
        try:
            return process_bookmark_file(processor_url, file_path, max_workers, min_chunk_size, max_chunk_size, memory_target)
        except Exception as e:
            return {"error": str(e)}
    
    # Verarbeite Dateien parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        future_to_file = {executor.submit(process_file, file): file for file in files}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_file)):
            file = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
                if "error" in result:
                    print(f"  Fehler bei Datei {i+1}: {result['error']}")
                else:
                    print(f"  Datei {i+1}/{num_files} verarbeitet: {result['items_processed']} Lesezeichen in {result['duration']:.2f} Sekunden")
            except Exception as e:
                print(f"  Fehler bei Datei {i+1}: {str(e)}")
    
    return results


def run_url_test(processor_url, num_url_batches, urls_per_batch, max_workers, min_chunk_size, max_chunk_size, memory_target):
    """Führt URL-Tests durch"""
    results = []
    
    print(f"URL-Test mit {num_url_batches} Batches, jeweils {urls_per_batch} URLs...")
    
    for i in range(num_url_batches):
        # Generiere URLs
        urls = [generate_random_url() for _ in range(urls_per_batch)]
        
        # Verarbeite URLs
        print(f"Verarbeite URL-Batch {i+1}/{num_url_batches}...")
        try:
            result = process_bookmark_urls(processor_url, urls, max_workers, min_chunk_size, max_chunk_size, memory_target)
            results.append(result)
            print(f"  URL-Batch {i+1} verarbeitet: {result['items_processed']} URLs in {result['duration']:.2f} Sekunden")
        except Exception as e:
            print(f"  Fehler bei URL-Batch {i+1}: {str(e)}")
    
    return results


def visualize_results(serial_results, parallel_results, url_results):
    """Visualisiert die Testergebnisse"""
    # Ergebnisse vorbereiten
    serial_times = [r['duration'] for r in serial_results if 'duration' in r]
    parallel_times = [r['duration'] for r in parallel_results if 'duration' in r]
    url_times = [r['duration'] for r in url_results if 'duration' in r]
    
    # Leere Listen behandeln
    if not serial_times and not parallel_times and not url_times:
        print("Keine Daten zum Visualisieren vorhanden")
        return
    
    # Plot erstellen
    plt.figure(figsize=(12, 8))
    
    # Testtypen
    test_types = []
    all_times = []
    
    if serial_times:
        test_types.append("Seriell")
        all_times.append(serial_times)
    
    if parallel_times:
        test_types.append("Parallel")
        all_times.append(parallel_times)
    
    if url_times:
        test_types.append("URLs")
        all_times.append(url_times)
    
    # Boxplot der Verarbeitungszeiten
    plt.subplot(2, 2, 1)
    plt.boxplot(all_times, labels=test_types)
    plt.title('Verarbeitungszeiten nach Testtyp')
    plt.ylabel('Zeit (Sekunden)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Histogramm der Verarbeitungszeiten
    plt.subplot(2, 2, 2)
    colors = ['blue', 'green', 'red']
    for i, times in enumerate(all_times):
        if times:  # Nur plotten, wenn Daten vorhanden sind
            plt.hist(times, alpha=0.5, label=test_types[i], color=colors[i % len(colors)])
    plt.title('Verteilung der Verarbeitungszeiten')
    plt.xlabel('Zeit (Sekunden)')
    plt.ylabel('Häufigkeit')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Mittlere Verarbeitungszeit pro Datei/Batch
    plt.subplot(2, 2, 3)
    means = [np.mean(times) if times else 0 for times in all_times]
    stds = [np.std(times) if times else 0 for times in all_times]
    plt.bar(test_types, means, yerr=stds, alpha=0.7)
    plt.title('Mittlere Verarbeitungszeit')
    plt.ylabel('Zeit (Sekunden)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Gesamtzeit pro Testtyp
    plt.subplot(2, 2, 4)
    totals = [np.sum(times) if times else 0 for times in all_times]
    plt.bar(test_types, totals, alpha=0.7)
    plt.title('Gesamtverarbeitungszeit')
    plt.ylabel('Zeit (Sekunden)')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    # Speichern und anzeigen
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"load_test_results_{timestamp}.png"
    plt.savefig(output_file)
    print(f"Ergebnisse wurden gespeichert unter: {output_file}")
    
    try:
        plt.show()
    except Exception as e:
        print(f"Konnte Plot nicht anzeigen: {str(e)}")


def main():
    """Hauptfunktion"""
    parser = argparse.ArgumentParser(description='Last-Test für den Bookmark-Processor')
    parser.add_argument('--url', default='http://localhost:5000', help='Prozessor-URL')
    parser.add_argument('--serial', action='store_true', help='Seriellen Test durchführen')
    parser.add_argument('--parallel', action='store_true', help='Parallelen Test durchführen')
    parser.add_argument('--urls', action='store_true', help='URL-Test durchführen')
    parser.add_argument('--num-bookmarks', type=int, default=100, help='Anzahl der Lesezeichen pro Datei')
    parser.add_argument('--num-files', type=int, default=5, help='Anzahl der Dateien')
    parser.add_argument('--max-concurrent', type=int, default=3, help='Maximale Anzahl gleichzeitiger Anfragen')
    parser.add_argument('--url-batches', type=int, default=5, help='Anzahl der URL-Batches')
    parser.add_argument('--urls-per-batch', type=int, default=50, help='Anzahl der URLs pro Batch')
    parser.add_argument('--max-workers', type=int, default=4, help='Maximale Anzahl Worker-Threads pro Anfrage')
    parser.add_argument('--min-chunk-size', type=int, default=10, help='Minimale Chunk-Größe')
    parser.add_argument('--max-chunk-size', type=int, default=1000, help='Maximale Chunk-Größe')
    parser.add_argument('--memory-target', type=int, default=70, help='Speicherziel in Prozent')
    parser.add_argument('--no-visualization', action='store_true', help='Keine Visualisierung anzeigen')
    
    args = parser.parse_args()
    
    # Standardmäßig alle Tests durchführen, wenn keine spezifiziert sind
    if not (args.serial or args.parallel or args.urls):
        args.serial = args.parallel = args.urls = True
    
    try:
        # Prüfen, ob der Processor erreichbar ist
        try:
            requests.get(f"{args.url}/health", timeout=5)
            print(f"Processor ist erreichbar unter {args.url}")
        except requests.RequestException as e:
            print(f"Warnung: Processor scheint nicht erreichbar zu sein: {str(e)}")
            if input("Möchten Sie trotzdem fortfahren? (j/n): ").lower() != 'j':
                return
        
        serial_results = []
        parallel_results = []
        url_results = []
        
        # Serieller Test
        if args.serial:
            serial_results = run_serial_test(
                args.url, args.num_bookmarks, args.num_files,
                args.max_workers, args.min_chunk_size, args.max_chunk_size, args.memory_target
            )
        
        # Paralleler Test
        if args.parallel:
            parallel_results = run_parallel_test(
                args.url, args.num_bookmarks, args.num_files, args.max_concurrent,
                args.max_workers, args.min_chunk_size, args.max_chunk_size, args.memory_target
            )
        
        # URL-Test
        if args.urls:
            url_results = run_url_test(
                args.url, args.url_batches, args.urls_per_batch,
                args.max_workers, args.min_chunk_size, args.max_chunk_size, args.memory_target
            )
        
        # Statistiken abrufen
        try:
            stats = get_processor_stats(args.url)
            print("\nProcessor-Statistiken:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        except Exception as e:
            print(f"Konnte Statistiken nicht abrufen: {str(e)}")
        
        # Ergebnisse visualisieren
        if not args.no_visualization:
            try:
                visualize_results(serial_results, parallel_results, url_results)
            except Exception as e:
                print(f"Fehler bei der Visualisierung: {str(e)}")
        
        # Ergebnisse in JSON speichern
        results = {
            "serial": serial_results,
            "parallel": parallel_results,
            "url": url_results,
            "timestamp": datetime.now().isoformat(),
            "config": vars(args)
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"load_test_results_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"Ergebnisse wurden gespeichert unter: {results_file}")
        
    except KeyboardInterrupt:
        print("\nTest wurde vom Benutzer abgebrochen")
    except Exception as e:
        print(f"Fehler bei der Testausführung: {str(e)}")


if __name__ == "__main__":
    main() 