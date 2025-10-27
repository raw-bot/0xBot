#!/usr/bin/env python3
"""
Script d'analyse des logs de décisions LLM
Analyse les fichiers de logs pour extraire des patterns et insights
"""
import os
import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Tuple


class LLMLogAnalyzer:
    """Analyse les logs de décisions LLM pour détecter des patterns"""
    
    def __init__(self, log_dir: str = "logs/llm_decisions"):
        self.log_dir = Path(log_dir)
        self.prompt_dir = self.log_dir / "prompts"
        self.response_dir = self.log_dir / "responses"
    
    def scan_logs(self) -> Tuple[List[Path], List[Path]]:
        """Scan les dossiers de logs"""
        prompts = sorted(self.prompt_dir.glob("*.prompt.txt")) if self.prompt_dir.exists() else []
        responses = sorted(self.response_dir.glob("*.response.txt")) if self.response_dir.exists() else []
        return prompts, responses
    
    def extract_metadata(self, filepath: Path) -> Dict:
        """Extrait les métadonnées d'un fichier de log"""
        metadata = {}
        
        with open(filepath, 'r', encoding='utf-8') as f:
            in_metadata = False
            for line in f:
                if line.strip() == "METADATA":
                    in_metadata = True
                    continue
                
                if in_metadata:
                    if line.strip() and ':' in line and not line.startswith('=') and not line.startswith('-'):
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
                    elif line.startswith('=') or line.startswith('-') or not line.strip():
                        break
        
        return metadata
    
    def extract_json_decision(self, filepath: Path) -> Dict:
        """Extrait la décision JSON parsée d'un fichier response"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find PARSED JSON DECISION section
        match = re.search(r'PARSED JSON DECISION\n=+\n\n(.*?)\n\n', content, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                return {}
        
        return {}
    
    def extract_reasoning(self, filepath: Path) -> str:
        """Extrait la section reasoning si présente"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find EXTRACTED REASONING section
        match = re.search(r'EXTRACTED REASONING.*?\n=+\n\n(.*?)\n\n', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return ""
    
    def analyze_all(self) -> Dict:
        """Analyse complète de tous les logs"""
        prompts, responses = self.scan_logs()
        
        print(f"📊 Analyzing {len(responses)} LLM decisions...")
        print(f"   Prompts: {len(prompts)}")
        print(f"   Responses: {len(responses)}")
        print()
        
        # Statistiques globales
        stats = {
            "total_decisions": len(responses),
            "actions": Counter(),
            "symbols": Counter(),
            "confidences": [],
            "has_reasoning": 0,
            "parsing_errors": 0,
            "by_hour": defaultdict(int),
            "by_symbol": defaultdict(lambda: {
                "entry": 0,
                "hold": 0,
                "exit": 0,
                "avg_confidence": []
            })
        }
        
        # Analyser chaque response
        for response_file in responses:
            metadata = self.extract_metadata(response_file)
            decision = self.extract_json_decision(response_file)
            reasoning = self.extract_reasoning(response_file)
            
            # Extraire l'action
            action = metadata.get('final_action', 'UNKNOWN')
            symbol = metadata.get('symbol', 'UNKNOWN')
            
            stats["actions"][action] += 1
            stats["symbols"][symbol] += 1
            
            # Timestamp analysis
            if 'timestamp' in metadata:
                try:
                    ts = datetime.fromisoformat(metadata['timestamp'])
                    hour = ts.hour
                    stats["by_hour"][hour] += 1
                except:
                    pass
            
            # Reasoning analysis
            if reasoning:
                stats["has_reasoning"] += 1
            
            # Decision analysis
            if decision:
                # Extract confidence
                symbol_key = symbol.replace('-', '/')
                if symbol_key in decision:
                    conf = decision[symbol_key].get('confidence', 0)
                    stats["confidences"].append(conf)
                    
                    # Per-symbol stats
                    stats["by_symbol"][symbol]["avg_confidence"].append(conf)
                    stats["by_symbol"][symbol][action.lower()] += 1
            else:
                stats["parsing_errors"] += 1
        
        return stats
    
    def print_report(self, stats: Dict) -> None:
        """Affiche un rapport d'analyse complet"""
        print("=" * 80)
        print("📈 LLM DECISION ANALYSIS REPORT")
        print("=" * 80)
        print()
        
        # Global stats
        print("GLOBAL STATISTICS")
        print("-" * 80)
        print(f"Total Decisions: {stats['total_decisions']}")
        print(f"Parsing Errors: {stats['parsing_errors']} ({stats['parsing_errors']/max(stats['total_decisions'],1)*100:.1f}%)")
        print(f"Decisions with Reasoning: {stats['has_reasoning']} ({stats['has_reasoning']/max(stats['total_decisions'],1)*100:.1f}%)")
        print()
        
        # Actions breakdown
        print("ACTIONS BREAKDOWN")
        print("-" * 80)
        for action, count in stats["actions"].most_common():
            pct = count / max(stats['total_decisions'], 1) * 100
            bar = "█" * int(pct / 2)
            print(f"  {action:8} | {count:4} ({pct:5.1f}%) {bar}")
        print()
        
        # Confidence analysis
        if stats["confidences"]:
            print("CONFIDENCE ANALYSIS")
            print("-" * 80)
            confs = stats["confidences"]
            print(f"  Average: {sum(confs)/len(confs):.3f}")
            print(f"  Min: {min(confs):.3f}")
            print(f"  Max: {max(confs):.3f}")
            print(f"  Median: {sorted(confs)[len(confs)//2]:.3f}")
            print()
        
        # Symbol breakdown
        print("SYMBOL BREAKDOWN")
        print("-" * 80)
        for symbol, count in stats["symbols"].most_common():
            pct = count / max(stats['total_decisions'], 1) * 100
            print(f"  {symbol:12} | {count:4} decisions ({pct:5.1f}%)")
        print()
        
        # Per-symbol action distribution
        print("PER-SYMBOL ACTION DISTRIBUTION")
        print("-" * 80)
        for symbol in sorted(stats["by_symbol"].keys()):
            data = stats["by_symbol"][symbol]
            total = data["entry"] + data["hold"] + data["exit"]
            avg_conf = sum(data["avg_confidence"]) / len(data["avg_confidence"]) if data["avg_confidence"] else 0
            
            print(f"  {symbol:12} | Total: {total:3}")
            print(f"    Entry: {data['entry']:3} | Hold: {data['hold']:3} | Exit: {data['exit']:3}")
            print(f"    Avg Confidence: {avg_conf:.3f}")
            print()
        
        # Hourly distribution
        if stats["by_hour"]:
            print("HOURLY DISTRIBUTION (UTC)")
            print("-" * 80)
            for hour in sorted(stats["by_hour"].keys()):
                count = stats["by_hour"][hour]
                bar = "█" * (count // 2)
                print(f"  {hour:02d}:00 | {count:4} decisions {bar}")
            print()
        
        # Insights & recommendations
        print("=" * 80)
        print("💡 INSIGHTS & RECOMMENDATIONS")
        print("=" * 80)
        
        # Check if bot is too conservative
        total_actions = sum(stats["actions"].values())
        hold_pct = stats["actions"].get("HOLD", 0) / max(total_actions, 1) * 100
        entry_pct = stats["actions"].get("ENTRY", 0) / max(total_actions, 1) * 100
        
        if hold_pct > 90:
            print("⚠️  Bot is EXTREMELY conservative (>90% HOLD)")
            print("    → Consider lowering confidence threshold from 75% to 65%")
            print("    → Review prompt for overly cautious instructions")
            print()
        
        if entry_pct < 5:
            print("⚠️  Very few ENTRY signals (<5%)")
            print("    → Bot may be missing opportunities")
            print("    → Check if stop loss/take profit requirements are too strict")
            print()
        
        # Check reasoning presence
        reasoning_pct = stats["has_reasoning"] / max(stats['total_decisions'], 1) * 100
        if reasoning_pct < 50:
            print("⚠️  Less than 50% of decisions have visible reasoning")
            print("    → LLM may not be using the STEP-BY-STEP REASONING section")
            print("    → Consider making reasoning section more prominent")
            print()
        
        # Check confidence levels
        if stats["confidences"]:
            avg_conf = sum(stats["confidences"]) / len(stats["confidences"])
            if avg_conf < 0.70:
                print(f"⚠️  Average confidence is low ({avg_conf:.2%})")
                print("    → LLM is uncertain about most decisions")
                print("    → May indicate unclear market conditions or ambiguous prompts")
                print()
        
        print("✅ Analysis complete!")
        print("=" * 80)
    
    def find_similar_patterns(self, min_confidence: float = 0.75) -> None:
        """Trouve les patterns de décisions similaires"""
        _, responses = self.scan_logs()
        
        print("\n🔍 Looking for high-confidence patterns...")
        print("-" * 80)
        
        high_conf_decisions = []
        
        for response_file in responses:
            metadata = self.extract_metadata(response_file)
            decision = self.extract_json_decision(response_file)
            
            if decision:
                symbol = metadata.get('symbol', '').replace('-', '/')
                if symbol in decision:
                    conf = decision[symbol].get('confidence', 0)
                    if conf >= min_confidence:
                        high_conf_decisions.append({
                            "file": response_file.name,
                            "symbol": symbol,
                            "action": metadata.get('final_action'),
                            "confidence": conf,
                            "timestamp": metadata.get('timestamp')
                        })
        
        if high_conf_decisions:
            print(f"Found {len(high_conf_decisions)} decisions with >={min_confidence:.0%} confidence:\n")
            for dec in sorted(high_conf_decisions, key=lambda x: x['confidence'], reverse=True):
                print(f"  {dec['confidence']:.1%} | {dec['action']:5} | {dec['symbol']:12} | {dec['timestamp']}")
        else:
            print(f"No decisions found with confidence >= {min_confidence:.0%}")


def main():
    """Main entry point"""
    import sys
    
    log_dir = sys.argv[1] if len(sys.argv) > 1 else "logs/llm_decisions"
    
    analyzer = LLMLogAnalyzer(log_dir)
    
    # Check if logs exist
    prompts, responses = analyzer.scan_logs()
    
    if not responses:
        print("❌ No log files found!")
        print(f"   Expected location: {log_dir}")
        print("\n💡 Make sure the bot has generated some logs first.")
        print("   Logs are created automatically when using the enhanced prompt service.")
        return
    
    # Run analysis
    stats = analyzer.analyze_all()
    analyzer.print_report(stats)
    
    # Find patterns
    analyzer.find_similar_patterns(min_confidence=0.75)


if __name__ == "__main__":
    main()
