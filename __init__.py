[
  {"id": 1, "name": "BTC Binance acima da SMA21", "active": true, "source": "binance", "symbol": "BTCUSDT", "metric": "dist_sma21", "operator": ">", "value": 0},
  {"id": 2, "name": "BTC Binance perdeu SMA21", "active": true, "source": "binance", "symbol": "BTCUSDT", "metric": "dist_sma21", "operator": "<", "value": 0},
  {"id": 3, "name": "BTC LSR surge positivo", "active": true, "source": "binance", "symbol": "BTCUSDT", "metric": "lsr_pct_change", "operator": ">", "value": 0.05},
  {"id": 4, "name": "BTC Taker Aggression forte", "active": true, "source": "binance", "symbol": "BTCUSDT", "metric": "aggression", "operator": ">", "value": 0.55},
  {"id": 5, "name": "ETH Dominance baixista", "active": true, "source": "binance", "symbol": "ETHUSDT", "metric": "dominance_pct", "operator": "<", "value": 45},
  {"id": 6, "name": "SOL Activity Score acelerando", "active": true, "source": "binance", "symbol": "SOLUSDT", "metric": "activity_zscore", "operator": ">", "value": 1.5},
  {"id": 7, "name": "BTC HL funding esticado", "active": true, "source": "hyperliquid", "symbol": "BTC", "metric": "funding", "operator": ">", "value": 0.0005},
  {"id": 8, "name": "BTC HL phi bull", "active": true, "source": "hyperliquid", "symbol": "BTC", "metric": "phi_score", "operator": ">=", "value": 4},
  {"id": 9, "name": "ETH HL OI elevado", "active": true, "source": "hyperliquid", "symbol": "ETH", "metric": "open_interest", "operator": ">", "value": 1000000},
  {"id": 10, "name": "SOL HL prêmio negativo", "active": true, "source": "hyperliquid", "symbol": "SOL", "metric": "premium", "operator": "<", "value": 0}
]
