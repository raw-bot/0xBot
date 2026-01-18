#!/usr/bin/env python3
"""
Live Trinity Signal Monitoring Dashboard
Monitors trading signals, confluence scores, and execution in real-time
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import re

# Add backend root to path
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))


class TrinityLiveMonitor:
    """Monitor Trinity signals live from bot logs"""

    def __init__(self, log_file="/var/folders/dj/420w389x3x9d3x_wd9n9640w0000gn/T/claude/-Users-cube/tasks/bedee75.output"):
        self.log_file = log_file
        self.last_position = 0
        self.signals_seen = []
        self.positions_open = {}
        self.trades_executed = 0

    def read_new_logs(self):
        """Read new log entries since last check"""
        try:
            with open(self.log_file, 'r') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
                return new_lines
        except FileNotFoundError:
            return []

    def parse_trinity_signal(self, line):
        """Extract Trinity signal information from log line"""
        # Pattern: [TRINITY] SYMBOL: signal_type | Confluence: X/100 | Signals: Y/5 | Confidence: Z%
        patterns = [
            r'\[TRINITY\]\s+(\w+/\w+):\s+BUY signal\s+\|\s+Confluence:\s+([\d.]+)/100\s+\|\s+Signals:\s+(\d+)/5\s+\|\s+Confidence:\s+([\d.]+)%',
            r'\[TRINITY\]\s+(\w+/\w+):\s+Entry conditions not met\s+\(([\d.]+)/5 signals\)',
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                if 'Entry conditions not met' in line:
                    return {
                        'symbol': match.group(1),
                        'type': 'SKIP',
                        'reason': f"{match.group(2)}/5 signals (insufficient)"
                    }
                else:
                    return {
                        'symbol': match.group(1),
                        'type': 'BUY',
                        'confluence': float(match.group(2)),
                        'signals_met': int(match.group(3)),
                        'confidence': float(match.group(4))
                    }
        return None

    def display_header(self):
        """Display monitoring dashboard header"""
        print("\n" + "="*100)
        print("🧪 TRINITY LIVE TRADING MONITOR - PHASE 3E")
        print("="*100)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: 📈 Trinity Indicator Framework")
        print(f"Log File: {self.log_file}")
        print("="*100)

    def display_signal(self, signal, timestamp):
        """Display a signal nicely formatted"""
        if signal['type'] == 'BUY':
            print(f"\n🟢 NEW SIGNAL at {timestamp}")
            print(f"   Symbol: {signal['symbol']}")
            print(f"   Type: BUY_TO_ENTER")
            print(f"   Confluence: {signal['confluence']:.0f}/100", end="")
            if signal['confluence'] >= 80:
                print(" ⭐⭐⭐ (Strong)")
            elif signal['confluence'] >= 60:
                print(" ⭐⭐ (Good)")
            else:
                print(" ⭐ (Moderate)")
            print(f"   Signals Met: {signal['signals_met']}/5")
            print(f"   Confidence: {signal['confidence']:.0f}%")

            # Position size recommendation
            if signal['confidence'] >= 0.8:
                size = "3.0%"
            elif signal['confidence'] >= 0.6:
                size = "2.0%"
            else:
                size = "1.0%"
            print(f"   Position Size: {size}")

            self.signals_seen.append({
                'symbol': signal['symbol'],
                'confluence': signal['confluence'],
                'confidence': signal['confidence'],
                'time': timestamp
            })
            self.trades_executed += 1

        elif signal['type'] == 'SKIP':
            print(f"\n⚫ SKIP at {timestamp}")
            print(f"   Symbol: {signal['symbol']}")
            print(f"   Reason: {signal['reason']}")

    def display_summary(self):
        """Display current trading summary"""
        if self.signals_seen:
            print("\n" + "-"*100)
            print("📊 SIGNALS GENERATED")
            print("-"*100)

            for i, sig in enumerate(self.signals_seen, 1):
                confluence_bar = "█" * int(sig['confluence'] / 10) + "░" * (10 - int(sig['confluence'] / 10))
                print(f"{i}. {sig['symbol']:10s} | Confluence: {confluence_bar} {sig['confluence']:5.0f}/100 | Confidence: {sig['confidence']:.0%} | {sig['time']}")

            avg_confluence = sum(s['confluence'] for s in self.signals_seen) / len(self.signals_seen)
            avg_confidence = sum(s['confidence'] for s in self.signals_seen) / len(self.signals_seen)

            print("-"*100)
            print(f"Total Signals: {len(self.signals_seen)} | Avg Confluence: {avg_confluence:.0f}/100 | Avg Confidence: {avg_confidence:.0%}")

    async def monitor(self, duration_minutes=10):
        """Monitor live trading for specified duration"""
        self.display_header()

        print(f"\n✅ Monitoring for {duration_minutes} minutes...")
        print("Waiting for Trinity signals...\n")

        start_time = datetime.now()
        check_interval = 2  # Check logs every 2 seconds

        try:
            while True:
                elapsed = (datetime.now() - start_time).total_seconds()

                if elapsed > duration_minutes * 60:
                    print("\n⏱️  Monitoring period complete!")
                    break

                new_logs = self.read_new_logs()

                for line in new_logs:
                    # Check for Trinity signals
                    signal = self.parse_trinity_signal(line)
                    if signal:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        self.display_signal(signal, timestamp)

                    # Check for trade execution
                    if "LONG " in line or "CLOSE" in line:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        print(f"\n💰 EXECUTION at {timestamp}")
                        print(f"   {line.strip()}")

                # Display periodic summary
                if int(elapsed) % 30 == 0 and elapsed > 0:
                    self.display_summary()

                await asyncio.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n\n⛔ Monitoring interrupted by user")

        # Final summary
        self.display_summary()
        self.display_final_report()

    def display_final_report(self):
        """Display final trading report"""
        print("\n" + "="*100)
        print("📈 FINAL TRADING REPORT")
        print("="*100)

        if self.signals_seen:
            print(f"\n✅ Total Signals Generated: {len(self.signals_seen)}")

            # Confidence distribution
            high_conf = len([s for s in self.signals_seen if s['confidence'] >= 0.8])
            med_conf = len([s for s in self.signals_seen if 0.6 <= s['confidence'] < 0.8])
            low_conf = len([s for s in self.signals_seen if s['confidence'] < 0.6])

            print(f"   High Confidence (80%+): {high_conf} signals")
            print(f"   Medium Confidence (60-80%): {med_conf} signals")
            print(f"   Low Confidence (<60%): {low_conf} signals")

            # Confluence distribution
            avg_confluence = sum(s['confluence'] for s in self.signals_seen) / len(self.signals_seen)
            print(f"\nAverage Confluence: {avg_confluence:.0f}/100")

            # By symbol
            symbols = {}
            for sig in self.signals_seen:
                if sig['symbol'] not in symbols:
                    symbols[sig['symbol']] = []
                symbols[sig['symbol']].append(sig)

            print(f"\nSignals by Symbol:")
            for sym, sigs in sorted(symbols.items()):
                avg_conf = sum(s['confluence'] for s in sigs) / len(sigs)
                print(f"   {sym:10s}: {len(sigs)} signal(s), Avg Confluence: {avg_conf:.0f}/100")

        else:
            print("\n⏳ No signals generated yet. Trinity waiting for confluence alignment.")
            print("   This is normal - Trinity only enters on 4-5 signal confluence.")

        print("\n" + "="*100)
        print("Status: 📈 Trinity framework actively monitoring markets")
        print("="*100 + "\n")


async def main():
    """Main monitoring loop"""
    monitor = TrinityLiveMonitor()

    # Monitor for 10 minutes (or until interrupted)
    await monitor.monitor(duration_minutes=10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
        sys.exit(0)
