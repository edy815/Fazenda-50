import asyncio, json, os
from aiohttp import web

devices = {}
panels = set()

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("type") == "register_client":
                    devices[data.get("id")] = ws
                    print(f"Cliente {data.get('id')} conectado. Total {len(devices)}")
                    await broadcast()
                elif data.get("type") == "register_panel":
                    panels.add(ws)
                    await ws.send_str(json.dumps({"type":"devices","devices":list(devices.keys()),"count":len(devices)}))
                elif data.get("type") == "command":
                    for w in list(devices.values()):
                        try:
                            await w.send_str(json.dumps({"type":"cmd","cmd":data.get("cmd"),"url":data.get("url","")}))
                        except: pass
    finally:
        for k,v in list(devices.items()):
            if v == ws: del devices[k]
        panels.discard(ws)
        await broadcast()
    return ws

async def broadcast():
    msg = json.dumps({"type":"devices","devices":list(devices.keys()),"count":len(devices)})
    for p in list(panels):
        try: await p.send_str(msg)
        except: pass

async def panel_handler(request):
    # lê o index original se existir, senão usa um básico
    html = open("panel.html","r",encoding="utf-8").read() if os.path.exists("panel.html") else open("index.html","r",encoding="utf-8").read() if os.path.exists("index.html") else None
    if html:
        return web.Response(text=html, content_type="text/html")
    # fallback
    return web.FileResponse("./client.html") if False else web.Response(text=open("server_panel.html","r").read() if os.path.exists("server_panel.html") else "Fazenda LIVE", content_type="text/html")

# vamos servir arquivos estáticos simples
async def init():
    app = web.Application()
    app.router.add_get('/ws', websocket_handler)
    app.router.add_get('/client', lambda r: web.FileResponse('client.html'))
    app.router.add_get('/', lambda r: web.FileResponse('client.html') if False else web.Response(text="""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{background:#111;color:#0f0;font-family:monospace;padding:10px}.box{border:2px solid #0f0;border-radius:10px;padding:10px;margin:10px 0}button{background:#0f0;color:#000;border:0;padding:10px 20px;margin:5px;border-radius:8px;font-weight:bold}</style>
</head><body>
<h2>🚜 Fazenda-50 is LIVE</h2>
<div class="box">Dispositivos: <b id="count">0</b><div id="list">Nenhum ainda</div></div>
<div class="box"><button onclick="sendCmd('open_tiktok')">Abrir TikTok</button><button onclick="sendCmd('like')">Dar Like</button><button onclick="sendCmd('follow')">Seguir</button><button onclick="sendCmd('scroll')">Rolar</button><br><br><input id="url" placeholder="URL" style="width:90%;padding:8px"><br><br><button onclick="sendUrl()">Enviar URL</button></div>
<div class="box" id="log"></div>
<script>
let ws=new WebSocket((location.protocol=='https:'?'wss://':'ws://')+location.host+'/ws');
ws.onopen=()=>{ws.send(JSON.stringify({type:'register_panel'}));}
ws.onmessage=(e)=>{let d=JSON.parse(e.data); if(d.type=='devices'){document.getElementById('count').innerText=d.count; document.getElementById('list').innerText=d.devices.join(', ')||'Nenhum ainda';}}
function sendCmd(c){ws.send(JSON.stringify({type:'command',cmd:c}));}
function sendUrl(){let u=document.getElementById('url').value; ws.send(JSON.stringify({type:'command',cmd:'open_url',url:u}));}
</script></body></html>
""", content_type="text/html"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    print("Fazenda-50 rodando")
    while True: await asyncio.sleep(3600)

asyncio.run(init())
