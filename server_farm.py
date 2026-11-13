import asyncio, json, os
from aiohttp import web

devices = {}
panels = set()

CLIENT_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{background:#000;color:#0f0;font-family:monospace;text-align:center;padding:30px}</style>
</head><body>
<h1>🚜 Fazenda-50 Cliente</h1>
<p id="status">Conectando...</p>
<p id="myid"></p>
<script>
let myId='cel-'+Math.random().toString(36).substr(2,6);
document.getElementById('myid').innerText='ID: '+myId;
let ws=new WebSocket((location.protocol=='https:'?'wss://':'ws://')+location.host+'/ws');
ws.onopen=()=>{ws.send(JSON.stringify({type:'register_client',id:myId})); document.getElementById('status').innerText='✅ CONECTADO - Aguardando comandos';}
ws.onmessage=(e)=>{let d=JSON.parse(e.data); if(d.type=='cmd'){ if(d.cmd=='open_tiktok') location.href='https://www.tiktok.com'; if(d.cmd=='open_url'&&d.url) location.href=d.url; }}
ws.onclose=()=>{document.getElementById('status').innerText='❌ Reconectando...'; setTimeout(()=>location.reload(),3000);}
</script>
</body></html>"""

PANEL_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{background:#111;color:#0f0;font-family:monospace;padding:10px}.box{border:2px solid #0f0;border-radius:10px;padding:10px;margin:10px 0}button{background:#0f0;color:#000;border:0;padding:10px 20px;margin:5px;border-radius:8px;font-weight:bold}input{width:90%;padding:8px}</style>
</head><body>
<h2>🚜 Fazenda-50 is LIVE</h2>
<div class="box">Server: fazenda-50.onrender.com<br>Status: ONLINE<br>Dispositivos conectados: <b id="count">0</b><div id="list">Nenhum ainda</div></div>
<div class="box"><b>Comandos</b><br><button onclick="sendCmd('open_tiktok')">Abrir TikTok</button><button onclick="sendCmd('like')">Dar Like</button><button onclick="sendCmd('follow')">Seguir</button><button onclick="sendCmd('scroll')">Rolar</button><br><br><input id="url" placeholder="Cole URL do TikTok"><br><br><button onclick="sendUrl()">Enviar URL</button></div>
<script>
let ws=new WebSocket((location.protocol=='https:'?'wss://':'ws://')+location.host+'/ws');
ws.onopen=()=>{ws.send(JSON.stringify({type:'register_panel'}));}
ws.onmessage=(e)=>{let d=JSON.parse(e.data); if(d.type=='devices'){document.getElementById('count').innerText=d.count; document.getElementById('list').innerText=d.devices.join(', ')||'Nenhum ainda';}}
function sendCmd(c){ws.send(JSON.stringify({type:'command',cmd:c}));}
function sendUrl(){let u=document.getElementById('url').value; ws.send(JSON.stringify({type:'command',cmd:'open_url',url:u}));}
</script></body></html>"""

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("type")=="register_client":
                    devices[data.get("id")]=ws
                    await broadcast()
                elif data.get("type")=="register_panel":
                    panels.add(ws)
                    await ws.send_str(json.dumps({"type":"devices","devices":list(devices.keys()),"count":len(devices)}))
                elif data.get("type")=="command":
                    for w in list(devices.values()):
                        try: await w.send_str(json.dumps({"type":"cmd","cmd":data.get("cmd"),"url":data.get("url","")}))
                        except: pass
    finally:
        for k,v in list(devices.items()):
            if v==ws: del devices[k]
        panels.discard(ws)
        await broadcast()
    return ws

async def broadcast():
    msg=json.dumps({"type":"devices","devices":list(devices.keys()),"count":len(devices)})
    for p in list(panels):
        try: await p.send_str(msg)
        except: pass

async def main():
    app=web.Application()
    app.router.add_get('/ws', ws_handler)
    app.router.add_get('/client', lambda r: web.Response(text=CLIENT_HTML, content_type='text/html'))
    app.router.add_get('/', lambda r: web.Response(text=PANEL_HTML, content_type='text/html'))
    runner=web.AppRunner(app)
    await runner.setup()
    site=web.TCPSite(runner,'0.0.0.0',int(os.environ.get("PORT",10000)))
    await site.start()
    print("Fazenda-50 rodando - sem dependencias de arquivo")
    while True: await asyncio.sleep(3600)

asyncio.run(main())
