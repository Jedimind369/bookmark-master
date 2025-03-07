#!/usr/bin/env python3

"""
api_client.py

Client für den Zugriff auf verschiedene LLM-APIs (QwQ, Claude, DeepSeek, GPT-4o Mini).
"""

import os
import json
import time
import logging
import asyncio
import aiohttp
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union

# Import für API-Monitoring
from scripts.monitoring import APIMonitor

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_client")

class ModelAPIClient:
    """Client für API-Aufrufe an verschiedene KI-Modelle mit integriertem Kosten-Monitoring."""

    def __init__(self, budget_limit: float = 20.0, monitor_enabled: bool = True):
        """Initialisiert den API-Client mit einem Budget-Limit."""
        self.budget_limit = budget_limit
        self.monitor_enabled = monitor_enabled
        
        # API-Monitor initialisieren, wenn aktiviert
        if self.monitor_enabled:
            from scripts.monitoring import APIMonitor
            self.api_monitor = APIMonitor(budget_limit=self.budget_limit)
            
            # Systemstatus speichern
            self.store_context("client_initialized", True)
            self.store_context("github_integration", "MCP Server verbunden")
            self.store_context("code_repository", "GitHub")
            self.store_context("workspace_path", "/Users/jedimind/Downloads/Coding/bookmark-master")
            
        # Cache für API-Aufrufe
        self.cache = {}
        
        self.api_keys = {
            "qwq": os.environ.get("QWQ_API_KEY", ""),
            "claude_sonnet": os.environ.get("CLAUDE_API_KEY", ""),
            "deepseek_r1": os.environ.get("DEEPSEEK_API_KEY", ""),
            "gpt4o_mini": os.environ.get("OPENAI_API_KEY", "")
        }
        
        # Cache für bereits getätigte API-Anfragen
        self.response_cache = {}
        
    async def call_model(self, model_id: str, prompt: str, max_tokens: int = 1000, use_cache: bool = True) -> Dict[str, Any]:
        """
        Ruft ein LLM-Modell mit dem gegebenen Prompt auf.
        
        Args:
            model_id: ID des Modells (qwq, claude_sonnet, deepseek_r1, gpt4o_mini)
            prompt: Der Prompt-Text
            max_tokens: Maximale Anzahl der Ausgabe-Tokens
            use_cache: Ob der Cache verwendet werden soll
            
        Returns:
            Dict mit der Modellantwort und Metadaten
        """
        # Prüfe Cache, wenn aktiviert
        cache_key = f"{model_id}:{prompt[:100]}"
        if use_cache and cache_key in self.response_cache:
            logger.info(f"Cache-Treffer für {model_id}")
            return self.response_cache[cache_key]
        
        # Zeitmessung starten
        start_time = time.time()
        
        try:
            # Modellspezifischer API-Aufruf
            if model_id == "qwq":
                result = await self._call_groq_api(prompt, max_tokens)
            elif model_id == "claude_sonnet":
                result = await self._call_anthropic_api(prompt, max_tokens)
            elif model_id == "deepseek_r1":
                result = await self._call_deepseek_api(prompt, max_tokens)
            elif model_id == "gpt4o_mini":
                result = await self._call_openai_api(prompt, max_tokens)
            else:
                raise ValueError(f"Unbekanntes Modell: {model_id}")
            
            # Zeitmessung beenden und Laufzeit berechnen
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # Metadaten zur Antwort hinzufügen
            result["elapsed_time"] = elapsed_time
            result["prompt"] = prompt
            
            # API-Kosten überwachen, wenn aktiviert
            if self.monitor_enabled and "cost" in result:
                task_name = f"bookmark-master-{model_id}"
                self.api_monitor.record_api_call(
                    model=model_id, 
                    cost=result["cost"], 
                    tokens_in=result.get("tokens_input", 0),
                    tokens_out=result.get("tokens_output", 0),
                    task=task_name
                )
            
            # Antwort cachen, wenn aktiviert
            if use_cache:
                self.response_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Fehler beim Aufruf von {model_id}: {str(e)}")
            return {
                "model": model_id,
                "error": str(e),
                "response": f"Fehler bei der API-Anfrage: {str(e)}",
                "elapsed_time": time.time() - start_time
            }
    
    async def _call_groq_api(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Ruft die Groq API für QwQ auf."""
        api_key = self.api_keys["qwq"]
        if not api_key:
            raise ValueError("QwQ API-Schlüssel nicht gefunden. Setze die Umgebungsvariable QWQ_API_KEY.")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "llama3-70b-8192",  # QwQ verwendet LLama 3
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            
            try:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Tokens zählen und Kosten schätzen
                        input_tokens = len(prompt.split())  # Ungefähre Schätzung
                        output_text = result["choices"][0]["message"]["content"]
                        output_tokens = len(output_text.split())  # Ungefähre Schätzung
                        
                        # Kosten berechnen ($0.25 pro 1M Input-Tokens, $0.75 pro 1M Output-Tokens)
                        input_cost = (input_tokens / 1000000) * 0.25
                        output_cost = (output_tokens / 1000000) * 0.75
                        total_cost = input_cost + output_cost
                        
                        return {
                            "model": "qwq",
                            "response": output_text,
                            "tokens_input": input_tokens,
                            "tokens_output": output_tokens,
                            "cost": total_cost
                        }
                    else:
                        error = await response.text()
                        raise Exception(f"Groq API-Fehler: {response.status} - {error}")
            except asyncio.TimeoutError:
                raise Exception("Timeout bei der Anfrage an die Groq API")
            except Exception as e:
                raise Exception(f"Fehler bei der Anfrage an die Groq API: {str(e)}")
    
    async def _call_anthropic_api(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Ruft die Anthropic API für Claude 3.7 Sonnet auf."""
        api_key = self.api_keys["claude_sonnet"]
        if not api_key:
            raise ValueError("Claude API-Schlüssel nicht gefunden. Setze die Umgebungsvariable CLAUDE_API_KEY.")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            data = {
                "model": "claude-3-sonnet-20240229",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            
            try:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=data,
                    timeout=120  # Längeres Timeout für Claude
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Tokens extrahieren, falls in der Antwort enthalten
                        input_tokens = result.get("usage", {}).get("input_tokens", len(prompt.split()))
                        output_tokens = result.get("usage", {}).get("output_tokens", len(result["content"][0]["text"].split()))
                        
                        # Kosten berechnen ($3.00 pro 1M Input-Tokens, $15.00 pro 1M Output-Tokens)
                        input_cost = (input_tokens / 1000000) * 3.00
                        output_cost = (output_tokens / 1000000) * 15.00
                        total_cost = input_cost + output_cost
                        
                        return {
                            "model": "claude_sonnet",
                            "response": result["content"][0]["text"],
                            "tokens_input": input_tokens,
                            "tokens_output": output_tokens,
                            "cost": total_cost
                        }
                    else:
                        error = await response.text()
                        raise Exception(f"Anthropic API-Fehler: {response.status} - {error}")
            except asyncio.TimeoutError:
                raise Exception("Timeout bei der Anfrage an die Anthropic API")
            except Exception as e:
                raise Exception(f"Fehler bei der Anfrage an die Anthropic API: {str(e)}")
    
    async def _call_deepseek_api(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Ruft die DeepSeek API für DeepSeek R1 auf."""
        api_key = self.api_keys["deepseek_r1"]
        if not api_key:
            raise ValueError("DeepSeek API-Schlüssel nicht gefunden. Setze die Umgebungsvariable DEEPSEEK_API_KEY.")
        
        # DeepSeek-Implementierung folgt ähnlichem Muster wie andere APIs
        # Für diesen Prototyp stellen wir eine einfache Implementierung bereit
        return {
            "model": "deepseek_r1",
            "response": f"DeepSeek R1 Antwort auf: {prompt[:50]}...",
            "tokens_input": len(prompt.split()),
            "tokens_output": 50,  # Dummy-Wert
            "cost": 0.01  # Dummy-Wert
        }
    
    async def _call_openai_api(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Ruft die OpenAI API für GPT-4o Mini auf."""
        api_key = self.api_keys["gpt4o_mini"]
        if not api_key:
            raise ValueError("OpenAI API-Schlüssel nicht gefunden. Setze die Umgebungsvariable OPENAI_API_KEY.")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
            
            try:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Tokens extrahieren
                        input_tokens = result.get("usage", {}).get("prompt_tokens", len(prompt.split()))
                        output_tokens = result.get("usage", {}).get("completion_tokens", len(result["choices"][0]["message"]["content"].split()))
                        
                        # Kosten berechnen ($0.15 pro 1M Input-Tokens, $0.60 pro 1M Output-Tokens)
                        input_cost = (input_tokens / 1000000) * 0.15
                        output_cost = (output_tokens / 1000000) * 0.60
                        total_cost = input_cost + output_cost
                        
                        return {
                            "model": "gpt4o_mini",
                            "response": result["choices"][0]["message"]["content"],
                            "tokens_input": input_tokens,
                            "tokens_output": output_tokens,
                            "cost": total_cost
                        }
                    else:
                        error = await response.text()
                        raise Exception(f"OpenAI API-Fehler: {response.status} - {error}")
            except asyncio.TimeoutError:
                raise Exception("Timeout bei der Anfrage an die OpenAI API")
            except Exception as e:
                raise Exception(f"Fehler bei der Anfrage an die OpenAI API: {str(e)}")

    def store_context(self, key: str, value: Any) -> None:
        """Speichert Kontextinformationen im API-Monitor."""
        if self.monitor_enabled and hasattr(self, 'api_monitor'):
            self.api_monitor.store_context_information(key, value)
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Ruft gespeicherte Kontextinformationen ab."""
        if self.monitor_enabled and hasattr(self, 'api_monitor'):
            return self.api_monitor.get_context_information(key, default)
        return default
    
    def list_all_context(self) -> Dict[str, Any]:
        """Listet alle gespeicherten Kontextinformationen auf."""
        if self.monitor_enabled and hasattr(self, 'api_monitor'):
            return self.api_monitor.list_all_context_information()
        return {}

# Einfacher Zugriff für synchrone Verwendung
async def call_model(model_id: str, prompt: str, max_tokens: int = 1000, use_cache: bool = True) -> Dict[str, Any]:
    """Einfache Funktion zum Aufrufen eines Modells."""
    client = ModelAPIClient()
    return await client.call_model(model_id, prompt, max_tokens, use_cache)

# Einfache Funktion zum Testen der API-Clients
async def test_api_clients():
    """Testet die verschiedenen API-Clients."""
    client = ModelAPIClient(budget_limit=10.0)
    test_prompt = "Erkläre mir kurz, was ein Bookmark-Management-System ist."
    
    # Teste QwQ
    try:
        result = await client.call_model("qwq", test_prompt)
        print(f"QwQ Antwort: {result['response'][:100]}...")
        print(f"Kosten: ${result['cost']:.6f}")
        
        # Zeige API-Nutzungsstatistik
        client.api_monitor.show_usage()
    except Exception as e:
        print(f"Fehler bei QwQ: {str(e)}")
    
    # Weitere Tests für andere Modelle können hier hinzugefügt werden

if __name__ == "__main__":
    asyncio.run(test_api_clients()) 