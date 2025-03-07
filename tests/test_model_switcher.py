#!/usr/bin/env python3

"""
test_model_switcher.py

Unit-Tests für die Funktionen in model_switcher.py.
"""

import sys
import unittest
from pathlib import Path

# Füge das Verzeichnis mit den Modulen zum Pfad hinzu
sys.path.append(str(Path(__file__).parent.parent / "scripts" / "ai"))

from model_switcher import analyze_complexity, assign_model, estimate_cost

class TestModelSwitcher(unittest.TestCase):
    """Tests für die Funktionen in model_switcher.py."""
    
    def test_analyze_complexity_simple(self):
        """Teste die Komplexitätsanalyse für einfache Prompts."""
        prompt = "Generate a function to add two numbers."
        result = analyze_complexity(prompt)
        
        self.assertEqual(result["complexity_level"], "simple")
        self.assertLessEqual(result["overall_score"], 30)  # Sollte unter dem Schwellenwert für simple liegen
        
    def test_analyze_complexity_security(self):
        """Teste die Erkennung von Sicherheits-Keywords."""
        prompt = "Test prompt with security and encryption considerations."
        result = analyze_complexity(prompt)
        
        self.assertGreater(len(result["security_matches"]), 0)  # Sollte Sicherheits-Keywords erkennen
        self.assertGreater(result["security_score"], 0)  # Score sollte erhöht sein
        
    def test_analyze_complexity_gdpr(self):
        """Teste die Erkennung von DSGVO-Keywords."""
        prompt = "How to handle personal data in compliance with GDPR and data protection."
        result = analyze_complexity(prompt)
        
        self.assertGreater(len(result["gdpr_matches"]), 0)  # Sollte DSGVO-Keywords erkennen
        self.assertGreater(result["gdpr_score"], 0)  # Score sollte erhöht sein
        
    def test_analyze_complexity_complex(self):
        """Teste die Komplexitätsanalyse für komplexe Prompts mit Code-Kontext."""
        prompt = "Optimize this asynchronous code to improve concurrency and reduce race conditions."
        code_context = """
        async def process_data(items):
            results = []
            for item in items:
                result = await process_item(item)
                results.append(result)
            return results
            
        async def process_item(item):
            # Complex processing
            await asyncio.sleep(1)
            return item * 2
        """
        
        result = analyze_complexity(prompt, code_context)
        
        self.assertEqual(result["complexity_level"], "medium")  # Sollte als mittlere Komplexität eingestuft werden
        self.assertGreater(result["code_complexity_score"], 0)  # Code-Komplexität sollte erkannt werden
        
    def test_assign_model_gdpr(self):
        """Teste die Modellzuweisung basierend auf DSGVO-Anforderungen."""
        # Einfacher Prompt mit DSGVO-Anforderung
        complexity = analyze_complexity("Simple prompt")
        model_with_gdpr = assign_model(complexity, gdpr_required=True)
        
        # Einfacher Prompt ohne DSGVO-Anforderung
        model_without_gdpr = assign_model(complexity, gdpr_required=False)
        
        # Mit GDPR sollte ein GDPR-konformes Modell gewählt werden
        self.assertNotEqual(model_with_gdpr, model_without_gdpr)
        
    def test_estimate_cost(self):
        """Teste die Kostenschätzung."""
        # Kurzer Text
        short_text = "This is a short prompt."
        short_cost = estimate_cost("gpt4o_mini", short_text)
        
        # Längerer Text
        long_text = "This is a longer prompt with more words to increase the token count significantly. " * 10
        long_cost = estimate_cost("gpt4o_mini", long_text)
        
        # Längerer Text sollte höhere Kosten verursachen
        self.assertGreater(long_cost, short_cost)

if __name__ == "__main__":
    unittest.main()
