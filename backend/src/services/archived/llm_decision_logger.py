"""LLM Decision Logger - Captures full decision process for debugging and analysis."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

SEPARATOR = "=" * 100
SUB_SEPARATOR = "-" * 100


class LLMDecisionLogger:
    """Logger for LLM decisions, creating separate prompt and response files."""

    def __init__(self, base_dir: str = "logs/llm_decisions"):
        self.base_dir = Path(base_dir)
        self.prompt_dir = self.base_dir / "prompts"
        self.response_dir = self.base_dir / "responses"
        self.prompt_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, symbol: str, action: str, timestamp: datetime) -> str:
        """Generate filename: YYYY-MM-DD_HH-MM-SS_SYMBOL_ACTION"""
        ts = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        sym = symbol.replace("/", "-").replace(":", "")
        return f"{ts}_{sym}_{action}"

    def _format_metadata(self, meta: Dict) -> str:
        """Format metadata as key: value lines."""
        return "\n".join(f"{k}: {v}" for k, v in meta.items())

    def _format_stats(self, text: str, label: str, extras: Optional[Dict] = None) -> str:
        """Format text statistics."""
        lines = [
            f"Lines: {text.count(chr(10))}",
            f"Characters: {len(text):,}",
            f"Estimated tokens: ~{len(text) // 4}",
        ]
        if extras:
            lines.extend(f"{k}: {v}" for k, v in extras.items())
        return "\n".join(lines)

    def log_decision(
        self,
        symbol: str,
        prompt: str,
        llm_raw_response: str,
        parsed_decision: Optional[Dict],
        final_action: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Log a complete LLM decision in two separate files (prompt and response)."""
        timestamp = datetime.now()
        base_filename = self._generate_filename(symbol, final_action, timestamp)

        meta = {**(metadata or {}), "symbol": symbol, "timestamp": timestamp.isoformat(), "final_action": final_action}
        meta_text = self._format_metadata(meta)

        # Write prompt file
        prompt_content = [
            SEPARATOR, "LLM DECISION LOG - PROMPT", SEPARATOR, "",
            "METADATA", SUB_SEPARATOR, meta_text, "",
            SEPARATOR, "FULL PROMPT SENT TO LLM", SEPARATOR, "", prompt, "",
            SEPARATOR, "PROMPT STATISTICS", SUB_SEPARATOR,
            self._format_stats(prompt, "prompt"), SEPARATOR,
        ]
        (self.prompt_dir / f"{base_filename}.prompt.txt").write_text("\n".join(prompt_content), encoding="utf-8")

        # Build response file content
        reasoning = self._extract_reasoning(llm_raw_response)
        parsed_json = json.dumps(parsed_decision, indent=2) if parsed_decision else "PARSING FAILED - No valid JSON found"

        summary_lines = []
        if parsed_decision:
            summary_lines.extend([
                f"Symbol: {symbol}",
                f"Action: {final_action}",
                f"Confidence: {parsed_decision.get('confidence', 'N/A')}",
            ])
            if final_action == "ENTRY":
                summary_lines.extend([
                    "", "Entry Details:",
                    f"  Entry Price: {parsed_decision.get('entry_price', 'N/A')}",
                    f"  Stop Loss: {parsed_decision.get('stop_loss', 'N/A')}",
                    f"  Profit Target: {parsed_decision.get('profit_target', 'N/A')}",
                    f"  Size %: {parsed_decision.get('size_pct', 'N/A')}",
                ])
            summary_lines.extend(["", f"Reasoning: {parsed_decision.get('justification', 'No justification provided')}"])
        else:
            summary_lines.append("No parsed decision available (parsing failed)")

        response_content = [
            SEPARATOR, "LLM DECISION LOG - RESPONSE & ANALYSIS", SEPARATOR, "",
            "METADATA", SUB_SEPARATOR, meta_text, "",
            SEPARATOR, "RAW LLM RESPONSE", SEPARATOR, "", llm_raw_response, "",
        ]
        if reasoning:
            response_content.extend([SEPARATOR, "EXTRACTED REASONING", SEPARATOR, "", reasoning, ""])
        response_content.extend([
            SEPARATOR, "PARSED JSON DECISION", SEPARATOR, "", parsed_json, "",
            SEPARATOR, "FINAL DECISION SUMMARY", SEPARATOR, "", "\n".join(summary_lines), "",
            SEPARATOR, "RESPONSE STATISTICS", SUB_SEPARATOR,
            self._format_stats(llm_raw_response, "response", {
                "Contains JSON": "Yes" if "{" in llm_raw_response else "No",
                "Contains reasoning": "Yes" if reasoning else "No",
            }),
            SEPARATOR,
        ])
        (self.response_dir / f"{base_filename}.response.txt").write_text("\n".join(response_content), encoding="utf-8")
    
    def _extract_reasoning(self, llm_response: str) -> Optional[str]:
        """Extract reasoning section from LLM response if present (text before JSON)."""
        if "{" in llm_response:
            pre_json = llm_response[:llm_response.index("{")].strip()
            if len(pre_json) > 50:
                return pre_json

        markers = ["let me think", "first, i need", "analyzing", "looking at", "considering", "my reasoning", "thought process"]
        if any(m in llm_response.lower() for m in markers):
            return llm_response.split("{")[0].strip() if "{" in llm_response else llm_response
        return None

    def log_error(
        self,
        symbol: str,
        prompt: str,
        error_message: str,
        llm_response: Optional[str] = None
    ) -> None:
        """Log an LLM decision error."""
        timestamp = datetime.now()
        base_filename = self._generate_filename(symbol, "ERROR", timestamp)

        content = [
            SEPARATOR, "LLM DECISION ERROR LOG", SEPARATOR, "",
            "ERROR DETAILS", SUB_SEPARATOR,
            f"Symbol: {symbol}",
            f"Timestamp: {timestamp.isoformat()}",
            f"Error: {error_message}", "",
        ]
        if llm_response:
            content.extend([SEPARATOR, "LLM RESPONSE (that caused error)", SEPARATOR, "", llm_response, ""])
        content.extend([SEPARATOR, "PROMPT THAT CAUSED ERROR", SEPARATOR, "", prompt])

        (self.base_dir / f"{base_filename}.error.txt").write_text("\n".join(content), encoding="utf-8")


_logger_instance: Optional[LLMDecisionLogger] = None


def get_llm_decision_logger() -> LLMDecisionLogger:
    """Get or create the global LLM decision logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = LLMDecisionLogger()
    return _logger_instance
