#!/usr/bin/env python3
"""
Verbesserter Beschreibungs-Generator für Lesezeichen.

Dieses Skript generiert Beschreibungen für Lesezeichen aus verschiedenen Quellen:
1. Meta-Description-Tag
2. Open Graph Description
3. Twitter Card Description
4. Erster Absatz des Hauptinhalts
5. Zusammenfassung aus den ersten Absätzen
"""

import os
import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import random
from tqdm import tqdm

# Add the project root to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent))

class ImprovedDescriptionGenerator:
    """
    Verbesserter Beschreibungs-Generator für Lesezeichen.
    """
    
    def __init__(self, max_workers=3, timeout=15, retry_count=2, 
                 delay_min=1, delay_max=3, user_agent=None):
        """
        Initialisiert den Beschreibungs-Generator.
        
        Args:
            max_workers: Maximale Anzahl gleichzeitiger Worker
            timeout: Timeout für Anfragen in Sekunden
            retry_count: Anzahl der Wiederholungsversuche bei fehlgeschlagenen Anfragen
            delay_min: Minimale Verzögerung zwischen Anfragen in Sekunden
            delay_max: Maximale Verzögerung zwischen Anfragen in Sekunden
            user_agent: User-Agent-String für Anfragen
        """
        self.timeout = timeout
        self.retry_count = retry_count
        self.delay_min = delay_min
        self.delay_max = delay_max
        
        if user_agent is None:
            self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        else:
            self.user_agent = user_agent
        
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        
        # Statistiken
        self.stats = {
            'success': 0,
            'error': 0,
            'retry': 0,
            'no_description': 0,
            'meta_description': 0,
            'og_description': 0,
            'twitter_description': 0,
            'first_paragraph': 0,
            'summary': 0
        }
    
    def extract_description(self, response, url):
        """
        Extrahiert eine Beschreibung aus einer HTTP-Antwort.
        
        Args:
            response: HTTP-Antwort
            url: URL der Webseite
            
        Returns:
            Extrahierte Beschreibung
        """
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Meta-Description-Tag
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc.get('content').strip()
                if len(description) > 20:
                    self.stats['meta_description'] += 1
                    return description
            
            # 2. Open Graph Description
            og_desc = soup.find('meta', attrs={'property': 'og:description'})
            if og_desc and og_desc.get('content'):
                description = og_desc.get('content').strip()
                if len(description) > 20:
                    self.stats['og_description'] += 1
                    return description
            
            # 3. Twitter Card Description
            twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
            if twitter_desc and twitter_desc.get('content'):
                description = twitter_desc.get('content').strip()
                if len(description) > 20:
                    self.stats['twitter_description'] += 1
                    return description
            
            # 4. Erster Absatz des Hauptinhalts
            main_content = soup.find('main') or soup.find('article') or soup.find('div', attrs={'id': 'content'}) or soup.find('div', attrs={'class': 'content'})
            if main_content:
                paragraphs = main_content.find_all('p')
                if paragraphs:
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) > 50:
                            self.stats['first_paragraph'] += 1
                            return text[:300] + ('...' if len(text) > 300 else '')
            
            # 5. Zusammenfassung aus den ersten Absätzen
            all_paragraphs = soup.find_all('p')
            if all_paragraphs:
                texts = []
                for p in all_paragraphs[:5]:  # Erste 5 Absätze
                    text = p.get_text().strip()
                    if len(text) > 30:
                        texts.append(text)
                
                if texts:
                    summary = ' '.join(texts)
                    self.stats['summary'] += 1
                    return summary[:300] + ('...' if len(summary) > 300 else '')
            
            # Keine Beschreibung gefunden
            self.stats['no_description'] += 1
            return ""
        
        except Exception as e:
            print(f"Fehler bei der Extraktion der Beschreibung für {url}: {str(e)}")
            return ""
    
    def generate_description(self, bookmark):
        """
        Generiert eine Beschreibung für ein Lesezeichen.
        
        Args:
            bookmark: Lesezeichen-Daten
            
        Returns:
            Angereicherte Lesezeichen-Daten
        """
        url = bookmark['url']
        enriched = bookmark.copy()
        
        # Überspringe, wenn bereits eine Beschreibung vorhanden ist
        if enriched.get('description'):
            return enriched
        
        # Versuche, die Webseite abzurufen
        for attempt in range(self.retry_count + 1):
            try:
                # Zufällige Verzögerung, um Rate-Limiting zu vermeiden
                if attempt > 0:
                    self.stats['retry'] += 1
                    delay = random.uniform(self.delay_min * 2, self.delay_max * 2)
                else:
                    delay = random.uniform(self.delay_min, self.delay_max)
                
                time.sleep(delay)
                
                # Anfrage senden
                response = self.session.get(url, timeout=self.timeout)
                
                # Beschreibung extrahieren, wenn erfolgreich
                if response.status_code == 200:
                    description = self.extract_description(response, url)
                    if description:
                        enriched['description'] = description
                    
                    self.stats['success'] += 1
                    return enriched
            
            except Exception as e:
                print(f"Fehler beim Abrufen von {url}: {str(e)}")
        
        # Fehler nach allen Versuchen
        self.stats['error'] += 1
        return enriched
    
    def generate_descriptions(self, input_file, output_file):
        """
        Generiert Beschreibungen für alle Lesezeichen in einer Datei.
        
        Args:
            input_file: Pfad zur Eingabe-JSON-Datei
            output_file: Pfad zur Ausgabe-JSON-Datei
        """
        # Lade die Lesezeichen
        with open(input_file, 'r', encoding='utf-8') as f:
            bookmarks = json.load(f)
        
        print(f"Geladen: {len(bookmarks)} Lesezeichen aus {input_file}")
        
        # Verarbeite jedes Lesezeichen
        enriched_bookmarks = []
        for bookmark in tqdm(bookmarks, desc="Generiere Beschreibungen"):
            enriched = self.generate_description(bookmark)
            enriched_bookmarks.append(enriched)
        
        # Speichere die angereicherten Lesezeichen
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_bookmarks, f, indent=2)
        
        print(f"Gespeichert: {len(enriched_bookmarks)} angereicherte Lesezeichen in {output_file}")
        
        # Zeige Statistiken
        print("\nStatistiken:")
        print(f"Erfolgreiche Anfragen: {self.stats['success']}")
        print(f"Fehlgeschlagene Anfragen: {self.stats['error']}")
        print(f"Wiederholungsversuche: {self.stats['retry']}")
        print(f"Keine Beschreibung gefunden: {self.stats['no_description']}")
        print(f"Beschreibungen aus Meta-Tags: {self.stats['meta_description']}")
        print(f"Beschreibungen aus Open Graph: {self.stats['og_description']}")
        print(f"Beschreibungen aus Twitter Cards: {self.stats['twitter_description']}")
        print(f"Beschreibungen aus ersten Absätzen: {self.stats['first_paragraph']}")
        print(f"Beschreibungen aus Zusammenfassungen: {self.stats['summary']}")

def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generiert verbesserte Beschreibungen für Lesezeichen")
    parser.add_argument("input_file", help="Pfad zur Eingabe-JSON-Datei")
    parser.add_argument("--output-file", default="data/enriched/enriched_with_descriptions.json",
                        help="Pfad zur Ausgabe-JSON-Datei")
    parser.add_argument("--timeout", type=int, default=15,
                        help="Timeout für Anfragen in Sekunden")
    parser.add_argument("--retry-count", type=int, default=2,
                        help="Anzahl der Wiederholungsversuche bei fehlgeschlagenen Anfragen")
    
    args = parser.parse_args()
    
    # Erstelle das Ausgabeverzeichnis, falls es nicht existiert
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
    
    # Initialisiere den Beschreibungs-Generator
    generator = ImprovedDescriptionGenerator(
        timeout=args.timeout,
        retry_count=args.retry_count
    )
    
    # Generiere Beschreibungen
    generator.generate_descriptions(args.input_file, args.output_file)

if __name__ == "__main__":
    main() 