import asyncio, websockets, json, os

DEVICES = {}
CONTROLLERS = set()

async def handle_device(ws, device_id, name):
    DEVICES[device_id] = {"ws": ws, "name": name}
    print(f"[+] {device_id} - Total: {len(DEVICES)}/50")
    try:
        async for msg in ws:
            data = json.loads(msg)
            data["device_id"] = device_id
            for ctrl in list(CONTROLLERS):
                try: await ctrl.send(json.dumps(data))
                except: CONTROLLERS.discard(ctrl)
    finally:
        DEVICES.pop(device_id, None)

async def handle_controller(ws):
    CONTROLLERS.add(ws)
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
    port = int(os.environ.get("PORT", 8765))
    print(f"Fazenda rodando na porta {port}")
    async with websockets.serve(handler, "0.0.0.0", port, max_size=10_000_000):
        await asyncio.Future()

asyncio.run(main())
