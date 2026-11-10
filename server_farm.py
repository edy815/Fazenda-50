import asyncio, websockets, json
from datetime import datetime

DEVICES = {}
CONTROLLERS = set()

async def handle_device(ws, device_id, name):
    DEVICES[device_id] = {"ws": ws, "name": name}
    print(f"[+] CELULAR: {device_id} ({name}) - Total: {len(DEVICES)}/50")
    try:
        async for msg in ws:
            data = json.loads(msg)
            data["device_id"] = device_id
            for ctrl in list(CONTROLLERS):
                try: await ctrl.send(json.dumps(data))
                except: CONTROLLERS.discard(ctrl)
    finally:
        DEVICES.pop(device_id, None)
        print(f"[-] Saiu: {device_id} - Total: {len(DEVICES)}/50")

async def handle_controller(ws):
    CONTROLLERS.add(ws)
    print(f"[PC] Conectado - Celulares online: {len(DEVICES)}")
    await ws.send(json.dumps({"type": "device_list", "devices": list(DEVICES.keys())}))
    try:
        async for msg in ws:
            data = json.loads(msg)
            target = data.get("target_device")
            if target in DEVICES:
                await DEVICES[target]["ws"].send(json.dumps(data))
    finally:
        CONTROLLERS.discard(ws)

async def handler(ws):
    info = json.loads(await ws.recv())
    if info.get("role") == "device":
        await handle_device(ws, info.get("device_id"), info.get("name"))
    else:
        await handle_controller(ws)

async def main():
    print("=== FAZENDA 50 CELULARES - 0.0.0.0:8765 ===")
    async with websockets.serve(handler, "0.0.0.0", 8765, max_size=10_000_000):
        await asyncio.Future()

asyncio.run(main())