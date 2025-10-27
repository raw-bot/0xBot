"""
Service de logging détaillé pour les décisions LLM
Capture TOUT le processus de décision pour debug et analyse
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class LLMDecisionLogger:
    """
    Logger dédié aux décisions LLM
    Crée 2 fichiers séparés pour une analyse précise
    """
    
    def __init__(self, base_dir: str = "logs/llm_decisions"):
        """
        Initialize logger
        
        Args:
            base_dir: Base directory for logs (default: logs/llm_decisions)
        """
        self.base_dir = Path(base_dir)
        
        # Créer les sous-dossiers
        self.prompt_dir = self.base_dir / "prompts"
        self.response_dir = self.base_dir / "responses"
        
        # Créer les dossiers s'ils n'existent pas
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, symbol: str, action: str, timestamp: datetime) -> str:
        """
        Generate filename based on timestamp, symbol, and action
        Format: 2025-10-27_20-31-20_BTC-USDT_HOLD
        """
        ts_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        symbol_clean = symbol.replace("/", "-").replace(":", "")
        return f"{ts_str}_{symbol_clean}_{action}"
    
    def log_decision(
        self,
        symbol: str,
        prompt: str,
        llm_raw_response: str,
        parsed_decision: Optional[Dict],
        final_action: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Log une décision LLM complète dans 2 fichiers séparés
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            prompt: Le prompt complet envoyé au LLM
            llm_raw_response: La réponse brute du LLM (avant parsing)
            parsed_decision: Le JSON parsé (ou None si échec parsing)
            final_action: L'action finale (ENTRY, HOLD, EXIT)
            metadata: Métadonnées additionnelles (confidence, price, etc.)
        """
        timestamp = datetime.now()
        base_filename = self._generate_filename(symbol, final_action, timestamp)
        
        # Metadata par défaut
        meta = metadata or {}
        meta.update({
            "symbol": symbol,
            "timestamp": timestamp.isoformat(),
            "final_action": final_action
        })
        
        # ========================================
        # FICHIER 1 : PROMPT COMPLET
        # ========================================
        prompt_file = self.prompt_dir / f"{base_filename}.prompt.txt"
        
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write("=" * 100 + "\n")
            f.write("LLM DECISION LOG - PROMPT\n")
            f.write("=" * 100 + "\n\n")
            
            # Metadata section
            f.write("METADATA\n")
            f.write("-" * 100 + "\n")
            for key, value in meta.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # Full prompt
            f.write("=" * 100 + "\n")
            f.write("FULL PROMPT SENT TO LLM\n")
            f.write("=" * 100 + "\n\n")
            f.write(prompt)
            f.write("\n\n")
            
            # Stats
            prompt_lines = prompt.count('\n')
            prompt_chars = len(prompt)
            f.write("=" * 100 + "\n")
            f.write("PROMPT STATISTICS\n")
            f.write("-" * 100 + "\n")
            f.write(f"Lines: {prompt_lines}\n")
            f.write(f"Characters: {prompt_chars:,}\n")
            f.write(f"Estimated tokens: ~{prompt_chars // 4}\n")
            f.write("=" * 100 + "\n")
        
        # ========================================
        # FICHIER 2 : RÉPONSE LLM + ANALYSE
        # ========================================
        response_file = self.response_dir / f"{base_filename}.response.txt"
        
        with open(response_file, "w", encoding="utf-8") as f:
            f.write("=" * 100 + "\n")
            f.write("LLM DECISION LOG - RESPONSE & ANALYSIS\n")
            f.write("=" * 100 + "\n\n")
            
            # Metadata section
            f.write("METADATA\n")
            f.write("-" * 100 + "\n")
            for key, value in meta.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # ========================================
            # SECTION 1 : RAW LLM RESPONSE
            # ========================================
            f.write("=" * 100 + "\n")
            f.write("RAW LLM RESPONSE (Unprocessed)\n")
            f.write("=" * 100 + "\n\n")
            f.write(llm_raw_response)
            f.write("\n\n")
            
            # ========================================
            # SECTION 2 : EXTRACTED REASONING (if present)
            # ========================================
            reasoning = self._extract_reasoning(llm_raw_response)
            if reasoning:
                f.write("=" * 100 + "\n")
                f.write("EXTRACTED REASONING (LLM's thought process)\n")
                f.write("=" * 100 + "\n\n")
                f.write(reasoning)
                f.write("\n\n")
            
            # ========================================
            # SECTION 3 : PARSED JSON
            # ========================================
            f.write("=" * 100 + "\n")
            f.write("PARSED JSON DECISION\n")
            f.write("=" * 100 + "\n\n")
            if parsed_decision:
                f.write(json.dumps(parsed_decision, indent=2))
            else:
                f.write("⚠️ PARSING FAILED - No valid JSON found\n")
            f.write("\n\n")
            
            # ========================================
            # SECTION 4 : FINAL DECISION SUMMARY
            # ========================================
            f.write("=" * 100 + "\n")
            f.write("FINAL DECISION SUMMARY\n")
            f.write("=" * 100 + "\n\n")
            
            if parsed_decision:
                f.write(f"Symbol: {symbol}\n")
                f.write(f"Action: {final_action}\n")
                f.write(f"Confidence: {parsed_decision.get('confidence', 'N/A')}\n")
                
                if final_action == "ENTRY":
                    f.write(f"\nEntry Details:\n")
                    f.write(f"  Entry Price: {parsed_decision.get('entry_price', 'N/A')}\n")
                    f.write(f"  Stop Loss: {parsed_decision.get('stop_loss', 'N/A')}\n")
                    f.write(f"  Profit Target: {parsed_decision.get('profit_target', 'N/A')}\n")
                    f.write(f"  Size %: {parsed_decision.get('size_pct', 'N/A')}\n")
                
                f.write(f"\nReasoning Summary:\n")
                f.write(f"  {parsed_decision.get('justification', 'No justification provided')}\n")
            else:
                f.write("⚠️ No parsed decision available (parsing failed)\n")
            
            f.write("\n")
            
            # ========================================
            # SECTION 5 : STATISTICS
            # ========================================
            f.write("=" * 100 + "\n")
            f.write("RESPONSE STATISTICS\n")
            f.write("-" * 100 + "\n")
            response_lines = llm_raw_response.count('\n')
            response_chars = len(llm_raw_response)
            f.write(f"Lines: {response_lines}\n")
            f.write(f"Characters: {response_chars:,}\n")
            f.write(f"Estimated tokens: ~{response_chars // 4}\n")
            f.write(f"Contains JSON: {'Yes' if '{' in llm_raw_response else 'No'}\n")
            f.write(f"Contains reasoning: {'Yes' if reasoning else 'No'}\n")
            f.write("=" * 100 + "\n")
    
    def _extract_reasoning(self, llm_response: str) -> Optional[str]:
        """
        Extract reasoning section from LLM response if present
        Looks for common patterns like:
        - "Let me think..."
        - "First, I need to..."
        - "Analyzing..."
        """
        # Look for reasoning before JSON
        if '{' in llm_response:
            json_start = llm_response.index('{')
            pre_json = llm_response[:json_start].strip()
            
            # If there's substantial text before JSON, consider it reasoning
            if len(pre_json) > 50:
                return pre_json
        
        # Look for explicit reasoning markers
        reasoning_markers = [
            "Let me think",
            "First, I need to",
            "Analyzing",
            "Looking at",
            "Considering",
            "My reasoning",
            "Thought process"
        ]
        
        for marker in reasoning_markers:
            if marker.lower() in llm_response.lower():
                # Found reasoning marker
                return llm_response.split('{')[0].strip() if '{' in llm_response else llm_response
        
        return None
    
    def log_error(
        self,
        symbol: str,
        prompt: str,
        error_message: str,
        llm_response: Optional[str] = None
    ) -> None:
        """
        Log une erreur de décision LLM
        
        Args:
            symbol: Trading symbol
            prompt: Le prompt qui a causé l'erreur
            error_message: Message d'erreur
            llm_response: La réponse LLM si disponible
        """
        timestamp = datetime.now()
        base_filename = self._generate_filename(symbol, "ERROR", timestamp)
        
        error_file = self.base_dir / f"{base_filename}.error.txt"
        
        with open(error_file, "w", encoding="utf-8") as f:
            f.write("=" * 100 + "\n")
            f.write("LLM DECISION ERROR LOG\n")
            f.write("=" * 100 + "\n\n")
            
            f.write("ERROR DETAILS\n")
            f.write("-" * 100 + "\n")
            f.write(f"Symbol: {symbol}\n")
            f.write(f"Timestamp: {timestamp.isoformat()}\n")
            f.write(f"Error: {error_message}\n")
            f.write("\n")
            
            if llm_response:
                f.write("=" * 100 + "\n")
                f.write("LLM RESPONSE (that caused error)\n")
                f.write("=" * 100 + "\n\n")
                f.write(llm_response)
                f.write("\n\n")
            
            f.write("=" * 100 + "\n")
            f.write("PROMPT THAT CAUSED ERROR\n")
            f.write("=" * 100 + "\n\n")
            f.write(prompt)
            f.write("\n")


# Global singleton instance
_logger_instance: Optional[LLMDecisionLogger] = None


def get_llm_decision_logger() -> LLMDecisionLogger:
    """Get or create the global LLM decision logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = LLMDecisionLogger()
    return _logger_instance
