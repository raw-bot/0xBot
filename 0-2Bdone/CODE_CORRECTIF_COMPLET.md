# 🛠️ CODE CORRECTIF - Exits Automatiques

Ce fichier contient le code complet à ajouter au bot pour implémenter les exits automatiques.

---

## 📋 ÉTAPE 1 : Ajouter ces méthodes à votre classe de trading

```python
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


async def check_exit_conditions(self, position, current_price: float) -> bool:
    """
    Vérifier si une position doit être fermée automatiquement.
    
    Args:
        position: L'objet position à vérifier
        current_price: Le prix actuel du marché
    
    Returns:
        True si la position a été fermée, False sinon
    """
    
    # Calculer le temps de détention
    hold_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
    
    # Calculer le P&L %
    if position.side == "LONG":
        pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
    else:  # SHORT
        pnl_pct = ((position.entry_price - current_price) / position.entry_price) * 100
    
    # 1. STOP LOSS HIT (avec buffer 0.5% pour éviter les faux déclenchements)
    sl_threshold = position.stop_loss * 1.005 if position.side == "LONG" else position.stop_loss * 0.995
    
    if position.side == "LONG" and current_price <= sl_threshold:
        logger.warning(f"🛑 SL HIT: {position.symbol} @ ${current_price:,.2f} (SL: ${position.stop_loss:,.2f})")
        logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
        await self.execute_exit(position, reason="SL_HIT", price=current_price)
        return True
    
    if position.side == "SHORT" and current_price >= sl_threshold:
        logger.warning(f"🛑 SL HIT: {position.symbol} @ ${current_price:,.2f} (SL: ${position.stop_loss:,.2f})")
        logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
        await self.execute_exit(position, reason="SL_HIT", price=current_price)
        return True
    
    # 2. TAKE PROFIT HIT (avec buffer 0.5%)
    tp_threshold = position.take_profit * 0.995 if position.side == "LONG" else position.take_profit * 1.005
    
    if position.side == "LONG" and current_price >= tp_threshold:
        logger.info(f"🎯 TP HIT: {position.symbol} @ ${current_price:,.2f} (TP: ${position.take_profit:,.2f})")
        logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
        await self.execute_exit(position, reason="TP_HIT", price=current_price)
        return True
    
    if position.side == "SHORT" and current_price <= tp_threshold:
        logger.info(f"🎯 TP HIT: {position.symbol} @ ${current_price:,.2f} (TP: ${position.take_profit:,.2f})")
        logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
        await self.execute_exit(position, reason="TP_HIT", price=current_price)
        return True
    
    # 3. TIMEOUT - Position trop longue en perte
    if hold_hours > 24 and pnl_pct < -1.0:
        logger.warning(f"⏱️ TIMEOUT: {position.symbol} - Position trop longue en perte")
        logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
        await self.execute_exit(position, reason="TIMEOUT_LOSS", price=current_price)
        return True
    
    # 4. GRANDE PERTE - Protection contre les pertes importantes
    if pnl_pct < -2.5:
        logger.error(f"⚠️ LARGE LOSS: {position.symbol} - Perte importante détectée")
        logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
        await self.execute_exit(position, reason="LARGE_LOSS", price=current_price)
        return True
    
    # 5. STAGNATION PROLONGÉE - Position breakeven > 12h
    if hold_hours > 12 and abs(pnl_pct) < 0.5:
        logger.info(f"💤 STAGNATION: {position.symbol} - Aucun mouvement significatif")
        logger.info(f"   Hold time: {hold_hours:.1f}h | P&L: {pnl_pct:.2f}%")
        await self.execute_exit(position, reason="STAGNATION", price=current_price)
        return True
    
    # Position OK, pas de sortie nécessaire
    logger.debug(f"✓ {position.symbol}: Hold time {hold_hours:.1f}h | P&L {pnl_pct:.2f}% | No exit conditions met")
    return False


async def manage_positions(self) -> dict:
    """
    Gérer toutes les positions actives et vérifier les conditions de sortie.
    Cette fonction doit être appelée au début de chaque cycle de trading.
    
    Returns:
        dict: Statistiques sur les positions gérées
    """
    stats = {
        "total_positions": 0,
        "positions_checked": 0,
        "positions_closed": 0,
        "reasons": {}
    }
    
    try:
        # Récupérer toutes les positions actives
        positions = await self.get_active_positions()
        stats["total_positions"] = len(positions)
        
        if not positions:
            logger.debug("📍 No active positions to manage")
            return stats
        
        logger.info(f"📍 Managing {len(positions)} active position(s)")
        
        for position in positions:
            stats["positions_checked"] += 1
            
            try:
                # Récupérer le prix actuel
                current_price = await self.get_current_price(position.symbol)
                
                # Vérifier les conditions de sortie
                should_exit = await self.check_exit_conditions(position, current_price)
                
                if should_exit:
                    stats["positions_closed"] += 1
                    # Incrémenter le compteur de raison (si disponible)
                    reason = getattr(position, 'exit_reason', 'UNKNOWN')
                    stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1
                
            except Exception as e:
                logger.error(f"❌ Error checking position {position.symbol}: {e}")
                continue
        
        # Résumé
        if stats["positions_closed"] > 0:
            logger.info(f"✅ Position management: {stats['positions_closed']}/{stats['positions_checked']} closed")
            for reason, count in stats["reasons"].items():
                logger.info(f"   • {reason}: {count}")
        else:
            logger.debug(f"✓ All {stats['positions_checked']} positions are within normal parameters")
        
    except Exception as e:
        logger.error(f"❌ Error in manage_positions: {e}")
    
    return stats


async def execute_exit(self, position, reason: str, price: Optional[float] = None) -> bool:
    """
    Exécuter la fermeture d'une position.
    
    Args:
        position: La position à fermer
        reason: La raison de la fermeture (SL_HIT, TP_HIT, TIMEOUT, etc.)
        price: Le prix de sortie (optionnel, sera récupéré si None)
    
    Returns:
        bool: True si la fermeture a réussi, False sinon
    """
    try:
        # Récupérer le prix actuel si non fourni
        if price is None:
            price = await self.get_current_price(position.symbol)
        
        # Calculer le P&L
        if position.side == "LONG":
            pnl = (price - position.entry_price) * position.quantity
            pnl_pct = ((price - position.entry_price) / position.entry_price) * 100
        else:
            pnl = (position.entry_price - price) * position.quantity
            pnl_pct = ((position.entry_price - price) / position.entry_price) * 100
        
        # Log détaillé
        logger.info(f"🚪 CLOSING POSITION: {position.symbol}")
        logger.info(f"   Entry: ${position.entry_price:,.2f} → Exit: ${price:,.2f}")
        logger.info(f"   Quantity: {position.quantity} | Side: {position.side}")
        logger.info(f"   P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%)")
        logger.info(f"   Reason: {reason}")
        
        # Exécuter l'ordre de fermeture via l'exchange
        # NOTE: Adapter cette partie selon votre API d'exchange
        result = await self.exchange.close_position(
            symbol=position.symbol,
            quantity=position.quantity,
            side="SELL" if position.side == "LONG" else "BUY"
        )
        
        if result.get("status") == "FILLED":
            logger.info(f"✅ Position {position.symbol} closed successfully")
            
            # Mettre à jour la base de données
            await self.db.update_position(
                position_id=position.id,
                status="CLOSED",
                exit_price=price,
                exit_time=datetime.now(),
                exit_reason=reason,
                realized_pnl=pnl
            )
            
            return True
        else:
            logger.error(f"❌ Failed to close position {position.symbol}: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error executing exit for {position.symbol}: {e}")
        return False
```

---

## 📋 ÉTAPE 2 : Intégrer dans la boucle principale

```python
async def main_trading_loop(self):
    """
    Boucle principale de trading.
    CRITIQUE: manage_positions() doit être appelé EN PREMIER à chaque cycle.
    """
    
    logger.info("🚀 Starting trading bot...")
    
    while True:
        try:
            cycle_start = datetime.now()
            logger.info("=" * 80)
            logger.info(f"🤖 0xBot | {cycle_start.strftime('%H:%M:%S')}")
            
            # ✅ ÉTAPE 1 : GÉRER LES POSITIONS EXISTANTES (PRIORITÉ ABSOLUE)
            # Ceci doit être fait AVANT toute autre analyse
            logger.info("📍 Step 1/4: Managing existing positions...")
            position_stats = await self.manage_positions()
            
            # ✅ ÉTAPE 2 : ANALYSER LE MARCHÉ
            logger.info("📊 Step 2/4: Analyzing market context...")
            market_context = await self.analyze_market_context()
            
            # ✅ ÉTAPE 3 : GÉNÉRER LES DÉCISIONS
            logger.info("🧠 Step 3/4: Generating trading decisions...")
            decisions = await self.generate_decisions(market_context)
            
            # ✅ ÉTAPE 4 : EXÉCUTER LES DÉCISIONS
            logger.info("⚡ Step 4/4: Executing decisions...")
            execution_results = await self.execute_decisions(decisions)
            
            # Résumé du cycle
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            logger.info("─" * 80)
            logger.info(f"✅ Cycle completed in {cycle_duration:.1f}s | Next in 3min")
            logger.info(f"   Positions: {position_stats['total_positions']} active, {position_stats['positions_closed']} closed")
            logger.info(f"   Decisions: {len(decisions)} generated, {execution_results.get('executed', 0)} executed")
            logger.info("=" * 80)
            
            # Attendre 3 minutes
            await asyncio.sleep(180)
            
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            logger.exception(e)
            await asyncio.sleep(60)  # Attendre 1 min en cas d'erreur
```

---

## 📋 ÉTAPE 3 : Adapter à votre structure de données

### Si vos positions utilisent des noms de champs différents

```python
# Exemple d'adaptation
async def check_exit_conditions(self, position, current_price: float) -> bool:
    # Adapter ces noms de champs selon votre structure
    entry_time = position.entry_time or position.opened_at or position.created_at
    entry_price = position.entry_price or position.open_price
    stop_loss = position.stop_loss or position.sl
    take_profit = position.take_profit or position.tp
    side = position.side or position.position_side or position.direction
    quantity = position.quantity or position.size or position.amount
    
    # Reste du code...
```

### Si vous utilisez une API d'exchange différente

```python
async def execute_exit(self, position, reason: str, price: Optional[float] = None) -> bool:
    # Exemple pour Binance Futures
    result = await self.exchange.create_order(
        symbol=position.symbol,
        type='MARKET',
        side='SELL' if position.side == 'LONG' else 'BUY',
        amount=position.quantity,
        params={'reduceOnly': True}
    )
    
    # Exemple pour Bybit
    result = await self.exchange.create_order(
        symbol=position.symbol,
        type='Market',
        side='Sell' if position.side == 'Long' else 'Buy',
        qty=position.quantity,
        reduce_only=True
    )
    
    # Adapter selon votre exchange
```

---

## 🧪 ÉTAPE 4 : Tests recommandés

### Test 1 : Vérifier que la fonction est appelée

```python
# Ajouter des logs temporaires
async def manage_positions(self):
    logger.info("🔍 manage_positions() called")  # ← AJOUTER CECI
    # ... reste du code
```

Vérifier dans les logs :
```bash
tail -f backend.log | grep "manage_positions() called"
# Devrait apparaître toutes les 3 minutes
```

### Test 2 : Simuler un SL hit

```python
# Mode test : forcer un SL hit
async def check_exit_conditions(self, position, current_price: float) -> bool:
    # TEMPORAIRE - À RETIRER APRÈS TEST
    if position.symbol == "ETH/USDT":
        logger.info("🧪 TEST MODE: Forcing SL hit")
        await self.execute_exit(position, reason="TEST_SL_HIT", price=current_price)
        return True
    
    # Reste du code normal...
```

### Test 3 : Vérifier les logs de sortie

Chercher ces patterns dans les logs :
```bash
tail -f backend.log | grep -E "SL HIT|TP HIT|TIMEOUT|CLOSING POSITION|Position.*closed"
```

Vous devriez voir :
```
🛑 SL HIT: ETH/USDT @ $3,980.00 (SL: $3,980.00)
🚪 CLOSING POSITION: ETH/USDT
   Entry: $4,100.00 → Exit: $3,980.00
   P&L: -$14.00 (-2.93%)
✅ Position ETH/USDT closed successfully
```

---

## ⚠️ POINTS D'ATTENTION

### 1. Gérer les erreurs de connexion

```python
async def get_current_price(self, symbol: str) -> float:
    try:
        ticker = await self.exchange.fetch_ticker(symbol)
        return ticker['last']
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        # Retourner le dernier prix connu ou lever l'exception
        raise
```

### 2. Éviter les doubles fermetures

```python
async def execute_exit(self, position, reason: str, price: Optional[float] = None) -> bool:
    # Vérifier que la position est toujours ouverte
    if position.status != "OPEN":
        logger.warning(f"⚠️ Position {position.symbol} already closed")
        return False
    
    # Reste du code...
```

### 3. Gérer le slippage

```python
async def check_exit_conditions(self, position, current_price: float) -> bool:
    # Buffer de 0.5% pour éviter les faux déclenchements dus au slippage
    sl_threshold = position.stop_loss * 1.005  # LONG
    # Pour un short: sl_threshold = position.stop_loss * 0.995
```

---

## 📊 MONITORING

### Métriques à surveiller après implémentation

```python
# Ajouter dans vos logs
logger.info(f"""
📊 POSITION MANAGEMENT STATS (Last 24h):
   Total positions: {total_positions}
   Closed by SL: {sl_hits}
   Closed by TP: {tp_hits}
   Closed by Timeout: {timeouts}
   Average hold time: {avg_hold_time:.1f}h
   Win rate: {win_rate:.1f}%
""")
```

### Alertes à mettre en place

```python
# Si aucune position ne se ferme pendant 6h
if last_exit_time > 6 hours:
    logger.error("⚠️ ALERT: No positions closed in the last 6 hours!")
    # Envoyer notification

# Si trop de SL hits
if sl_rate > 80%:
    logger.warning("⚠️ WARNING: High SL hit rate - Review strategy")
```

---

## ✅ CHECKLIST FINALE

Avant de déployer :

- [ ] Code ajouté dans le fichier principal de trading
- [ ] `manage_positions()` appelé en PREMIER dans la boucle
- [ ] Testé avec une position existante
- [ ] Les logs montrent les vérifications SL/TP
- [ ] Une position test s'est fermée correctement
- [ ] Les buffers de prix sont adaptés à votre stratégie
- [ ] L'API d'exchange est correctement appelée
- [ ] Les erreurs sont gérées
- [ ] Le monitoring est en place

---

**🚀 Bon courage pour l'implémentation !**

Si vous avez des questions ou erreurs, les logs devraient vous guider.
Les points critiques sont :
1. Appeler `manage_positions()` EN PREMIER
2. Vérifier TOUTES les positions AVANT d'analyser le marché
3. Logger clairement chaque action
