"""
Quick diagnostic: connects directly to Bybit and OKX, prints the first
5 raw messages from each so we can see the exact JSON format they send.
Run from the ingestion/ directory:  python debug_ws.py
"""
import asyncio
import json
import websockets


async def sniff(label: str, url: str, subscribe_payload: dict, n: int = 5):
    print(f"\n{'='*60}")
    print(f"  {label}  —  {url}")
    print(f"{'='*60}")
    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            await ws.send(json.dumps(subscribe_payload))
            for i in range(n):
                raw = await asyncio.wait_for(ws.recv(), timeout=10)
                try:
                    parsed = json.loads(raw)
                    print(f"\n[msg {i+1}]  type={parsed.get('type')} action={parsed.get('action')} "
                          f"op={parsed.get('op')} success={parsed.get('success')}")
                    print(json.dumps(parsed, indent=2)[:600])
                except Exception:
                    print(f"\n[msg {i+1}]  RAW: {raw[:400]}")
    except Exception as exc:
        print(f"  ERROR: {exc}")


async def main():
    await sniff(
        "BYBIT V5 spot",
        "wss://stream.bybit.com/v5/public/spot",
        {"op": "subscribe", "args": ["tickers.BTCUSDT"]},
    )
    await sniff(
        "OKX V5 public",
        "wss://ws.okx.com:8443/ws/v5/public",
        {"op": "subscribe", "args": [{"channel": "tickers", "instId": "BTC-USDT"}]},
    )


if __name__ == "__main__":
    asyncio.run(main())
