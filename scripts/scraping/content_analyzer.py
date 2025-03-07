#!/usr/bin/env python3

"""
content_analyzer.py

Klasse zur Analyse von gescrapetem Inhalt mit verschiedenen AI-Modellen.
"""

import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Pfad zur Hauptanwendung hinzufügen, damit wir auf andere Module zugreifen können
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import der API-Client-Klasse
from scripts.ai.api_client import ModelAPIClient

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("content_analyzer")

class ContentAnalyzer:
    """
    Klasse zur Analyse von gescrapetem Inhalt mit verschiedenen AI-Modellen.
    Wählt das optimale Modell basierend auf der Inhaltskomplexität aus.
    """
    
    def __init__(self, output_dir: str = "data/analyzed", api_key: Optional[str] = None):
        """
        Initialisiert den ContentAnalyzer.
        
        Args:
            output_dir: Verzeichnis für die analysierten Daten
            api_key: API-Schlüssel für die verschiedenen LLM-Dienste (optional)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Modellgewichte für verschiedene Komplexitätsniveaus
        self.complexity_model_mapping = {
            "sehr_niedrig": "qwq",           # QwQ für sehr einfache Inhalte
            "niedrig": "qwq",                # QwQ für einfache Inhalte
            "mittel": "deepseek_r1",         # DeepSeek R1 für mittlere Komplexität
            "hoch": "gpt4o_mini",            # GPT-4o Mini für komplexere Inhalte
            "sehr_hoch": "claude_sonnet"     # Claude Sonnet für sehr komplexe Inhalte
        }
        
        # API-Client für den Zugriff auf die verschiedenen Modelle initialisieren
        self.api_client = ModelAPIClient()
        
        # Stat-Tracking für Modellaufrufe
        self.model_usage = {
            "qwq": {"uses": 0, "total_cost": 0},
            "deepseek_r1": {"uses": 0, "total_cost": 0},
            "gpt4o_mini": {"uses": 0, "total_cost": 0},
            "claude_sonnet": {"uses": 0, "total_cost": 0}
        }
    
    async def analyze_content(self, url: str, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analysiert den gescrapten Inhalt mit dem optimalen AI-Modell.
        
        Args:
            url: URL der gescrapten Seite
            scraped_data: Gescrapte Daten von der Zyte API
            
        Returns:
            Dict mit den analysierten Daten
        """
        try:
            # Extrahiere den Inhalt aus den gescrapten Daten
            content = self._extract_content(scraped_data)
            if not content:
                logger.warning(f"Kein Inhalt zum Analysieren für {url}")
                return {"url": url, "success": False, "error": "Kein Inhalt zum Analysieren"}
            
            # Schätze die Komplexität des Inhalts
            complexity = self._estimate_complexity(content)
            
            # Wähle das optimale Modell basierend auf der Komplexität und dem Inhalt
            model_id = self._select_optimal_model(content, complexity)
            logger.info(f"Verwende Modell {model_id} für {url} (Komplexität: {complexity})")
            
            # Generiere die Analyse mit dem ausgewählten Modell
            prompt = self._generate_prompt(url, content)
            result = await self.api_client.call_model(model_id, prompt)
            
            # Aktualisiere Modellnutzungsstatistiken
            self.model_usage[model_id]["uses"] += 1
            self.model_usage[model_id]["total_cost"] += result.get("cost", 0)
            
            # Verarbeite die Antwort zu einem standardisierten Format
            analyzed_data = self._process_response(result["response"], url, scraped_data)
            analyzed_data["model_used"] = model_id
            analyzed_data["complexity"] = complexity
            analyzed_data["model_cost"] = result.get("cost", 0)
            
            # Speichere die analysierten Daten
            output_file = self.output_dir / f"{self._get_safe_filename(url)}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analyzed_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Analyse für {url} abgeschlossen und gespeichert")
            return analyzed_data
            
        except Exception as e:
            logger.error(f"Fehler bei der Analyse von {url}: {str(e)}")
            return {"url": url, "success": False, "error": str(e)}
    
    def _extract_content(self, scraped_data: Dict[str, Any]) -> str:
        """
        Extrahiert den Inhalt aus den gescrapten Daten.
        
        Args:
            scraped_data: Gescrapte Daten von der Zyte API
            
        Returns:
            Extrahierter Inhalt als String
        """
        content = ""
        
        # Versuche, Hauptinhalt zu extrahieren
        article_body = scraped_data.get("articleBody", "")
        if article_body:
            content += article_body + "\n\n"
        
        # Versuche, Überschriften zu extrahieren
        headline = scraped_data.get("headline", "")
        if headline:
            content = headline + "\n\n" + content
        
        # Versuche, Metadaten zu extrahieren
        description = scraped_data.get("description", "")
        if description:
            content += "Beschreibung: " + description + "\n\n"
        
        # Wenn kein strukturierter Inhalt gefunden wurde, versuche allgemeine Textextraktion
        if not content:
            # Versuche, Textkörper zu finden
            if "product" in scraped_data:
                product = scraped_data["product"]
                if "description" in product:
                    content += "Produktbeschreibung: " + product["description"] + "\n\n"
            
            # Sammle Text aus verfügbaren Feldern
            for key in ["text", "pageContent", "content", "bodyText"]:
                if key in scraped_data and scraped_data[key]:
                    content += scraped_data[key] + "\n\n"
        
        return content.strip()
    
    def _estimate_complexity(self, content: str) -> str:
        """
        Schätzt die Komplexität des Inhalts basierend auf verschiedenen Faktoren.
        
        Args:
            content: Der zu analysierende Inhalt
            
        Returns:
            Komplexitätsniveau: sehr_niedrig, niedrig, mittel, hoch, sehr_hoch
        """
        # Einfache Heuristiken zur Bestimmung der Komplexität
        words = content.split()
        word_count = len(words)
        
        # Durchschnittliche Wortlänge berechnen
        avg_word_length = sum(len(word) for word in words) / max(1, word_count)
        
        # Komplexe Wörter zählen (Wörter mit mehr als 6 Buchstaben)
        complex_words = sum(1 for word in words if len(word) > 6)
        complex_word_ratio = complex_words / max(1, word_count)
        
        # Technische/wissenschaftliche Begriffe erkennen
        technical_terms = ["analyse", "methode", "studie", "forschung", "entwicklung", 
                          "algorithmus", "implementation", "system", "technologie",
                          "wissenschaft", "hypothese", "theorie", "experiment"]
        tech_term_count = sum(1 for word in words if word.lower() in technical_terms)
        
        # Komplexitätsniveau basierend auf den Heuristiken bestimmen
        if word_count < 100:
            return "sehr_niedrig"
        elif word_count < 300 and avg_word_length < 5 and complex_word_ratio < 0.1:
            return "niedrig"
        elif word_count < 800 and avg_word_length < 6 and complex_word_ratio < 0.2:
            return "mittel"
        elif word_count < 1500 or (tech_term_count > 10 and complex_word_ratio > 0.25):
            return "hoch"
        else:
            return "sehr_hoch"
    
    def _select_optimal_model(self, content: str, complexity: str) -> str:
        """
        Wählt das optimale Modell basierend auf Inhaltskomplexität und Schlüsselwörtern aus.
        
        Args:
            content: Der zu analysierende Inhalt
            complexity: Das berechnete Komplexitätsniveau
            
        Returns:
            ID des zu verwendenden Modells
        """
        # Standardmodell basierend auf Komplexität auswählen
        model_id = self.complexity_model_mapping.get(complexity, "qwq")
        
        # Spezifische Schlüsselwörter prüfen, die ein anderes Modell erfordern könnten
        content_lower = content.lower()
        
        # GDPR/DSGVO-bezogene Inhalte erfordern eine genauere Analyse
        if any(term in content_lower for term in ["gdpr", "dsgvo", "datenschutz", "privacy", "compliance"]):
            # Verwende mindestens DeepSeek R1 für DSGVO-bezogene Inhalte
            if model_id == "qwq":
                model_id = "deepseek_r1"
        
        # Sicherheitsrelevante Inhalte erfordern eine genauere Analyse
        if any(term in content_lower for term in ["security", "sicherheit", "verschlüsselung", "encryption", "authentication"]):
            # Verwende mindestens GPT-4o Mini für sicherheitsrelevante Inhalte
            if model_id in ["qwq", "deepseek_r1"]:
                model_id = "gpt4o_mini"
        
        # Juristische oder medizinische Inhalte erfordern die höchste Genauigkeit
        if any(term in content_lower for term in 
               ["gesetz", "law", "legal", "medizin", "medical", "diagnose", "treatment", "therapie"]):
            # Verwende Claude Sonnet für juristische oder medizinische Inhalte
            model_id = "claude_sonnet"
            
        return model_id
    
    def _generate_prompt(self, url: str, content: str) -> str:
        """
        Generiert einen Prompt für die AI-Analyse.
        
        Args:
            url: URL der Seite
            content: Extrahierter Inhalt
            
        Returns:
            Generierter Prompt für die AI
        """
        prompt = f"""
        Analysiere den folgenden Inhalt einer Webseite und extrahiere die wichtigsten Informationen.
        URL: {url}
        
        INHALT:
        {content[:4000]}  # Begrenzen, um Token-Limits einzuhalten
        
        Antworte im folgenden JSON-Format:
        {{
            "title": "Extrahierter oder generierter Titel",
            "summary": "Kurze Zusammenfassung des Inhalts (max. 2-3 Sätze)",
            "keywords": ["Schlüsselwort1", "Schlüsselwort2", ...],
            "main_topics": ["Hauptthema1", "Hauptthema2", ...],
            "content_type": "Typ des Inhalts (z.B. Artikel, Produktseite, Blog, Dokumentation)",
            "relevance_score": Relevanzwert von 1-10,
            "sentiment": "positiv", "neutral" oder "negativ"
        }}
        
        Antworte nur mit dem JSON-Objekt, ohne weiteren Text.
        """
        return prompt.strip()
    
    def _process_response(self, response: str, url: str, scraped_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet die Antwort des AI-Modells in ein standardisiertes Format.
        
        Args:
            response: Antwort des AI-Modells
            url: URL der Seite
            scraped_data: Originale gescrapte Daten
            
        Returns:
            Verarbeitete Analysedaten
        """
        try:
            # Extrahiere JSON aus der Antwort
            json_str = response
            
            # Wenn die Antwort Zusatztext enthält, versuche, JSON zu extrahieren
            if not json_str.strip().startswith('{'):
                import re
                json_matches = re.findall(r'({[\s\S]*})', json_str)
                if json_matches:
                    json_str = json_matches[0]
            
            analyzed_data = json.loads(json_str)
            
            # Füge Metadaten hinzu
            analyzed_data["url"] = url
            analyzed_data["success"] = True
            analyzed_data["timestamp"] = scraped_data.get("timestamp", "")
            
            return analyzed_data
            
        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung der AI-Antwort: {str(e)}")
            # Fallback auf einfache Datenstruktur
            return {
                "url": url,
                "success": True,
                "raw_response": response,
                "error_processing": str(e),
                "timestamp": scraped_data.get("timestamp", "")
            }
    
    def _get_safe_filename(self, url: str) -> str:
        """
        Erzeugt einen sicheren Dateinamen aus einer URL.
        
        Args:
            url: Die zu konvertierende URL
            
        Returns:
            Sicherer Dateiname
        """
        import re
        from hashlib import md5
        # Entferne das Protokoll (http://, https://)
        url_without_protocol = re.sub(r'^https?://', '', url)
        # Ersetze alle Nicht-Alphanumerischen Zeichen durch Unterstriche
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', url_without_protocol)
        # Kürze lange Namen und füge MD5-Hash hinzu
        if len(safe_name) > 100:
            hash_part = md5(url.encode()).hexdigest()[:10]
            safe_name = safe_name[:90] + '_' + hash_part
        return safe_name
    
    def get_model_usage_stats(self) -> Dict[str, Any]:
        """
        Gibt Statistiken zur Modellnutzung zurück.
        
        Returns:
            Dict mit Modellnutzungsstatistiken
        """
        total_uses = sum(model["uses"] for model in self.model_usage.values())
        total_cost = sum(model["total_cost"] for model in self.model_usage.values())
        
        stats = {
            "models": self.model_usage,
            "total_uses": total_uses,
            "total_cost": total_cost
        }
        
        return stats 