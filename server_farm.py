import asyncio, json, os
from aiohttp import web
import websockets
from websockets.server import serve

devices = {}
panel_clients = set()

async def ws_handler(websocket):
    try:
        async for msg in websocket:
            data = json.loads(msg)
            if data.get("type") == "register_client":
                # celular da fazenda
                dev_id = data.get("id", str(id(websocket)))
                devices[dev_id] = websocket
                print(f"Cliente conectado: {dev_id} Total: {len(devices)}")
                await broadcast_panel()
            elif data.get("type") == "register_panel":
                # seu painel
                panel_clients.add(websocket)
                await websocket.send(json.dumps({"type":"devices","devices":list(devices.keys()),"count":len(devices)}))
            elif data.get("type") == "command":
                # comando do painel para todos
                cmd = data.get("cmd")
                for ws in list(devices.values()):
                    try:
                        await ws.send(json.dumps({"type":"cmd","cmd":cmd,"url":data.get("url","")}))
                    except: pass
    except:
        pass
    finally:
        # limpar
        for k,v in list(devices.items()):
            if v == websocket:
                del devices[k]
        panel_clients.discard(websocket)
        await broadcast_panel()

async def broadcast_panel():
    msg = json.dumps({"type":"devices","devices":list(devices.keys()),"count":len(devices)})
    for ws in list(panel_clients):
        try:
            await ws.send(msg)
        except: pass

# Páginas HTML
PANEL_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{background:#111;color:#0f0;font-family:monospace;padding:10px}.box{border:2px solid #0f0;border-radius:10px;padding:10px;margin:10px 0}button{background:#0f0;color:#000;border:0;padding:10px 20px;margin:5px;border-radius:8px;font-weight:bold}</style>
</head><body>
<h2>🚜 Fazenda-50 is LIVE</h2>
<div class="box">Server: fazenda-50.onrender.com<br>Status: ONLINE<br>Dispositivos conectados: <b id="count">0</b></div>
<div class="box"><b>Lista de Celulares</b><div id="list">Nenhum ainda</div></div>
<div class="box"><b>Comandos</b><br>
<button onclick="sendCmd('open_tiktok')">Abrir TikTok</button>
<button onclick="sendCmd('like')">Dar Like</button>
<button onclick="sendCmd('follow')">Seguir</button>
<button onclick="sendCmd('scroll')">Rolar</button><br><br>
<input id="url" placeholder="URL / comando" style="width:90%;padding:8px"><br><br>
<button onclick="sendUrl()">Enviar URL</button></div>
<script>
let ws = new WebSocket((location.protocol=='https:'?'wss://':'ws://')+location.host+'/ws');
ws.onopen=()=>{ws.send(JSON.stringify({type:'register_panel'})); log('Conectado ao painel');}
ws.onmessage=(e)=>{let d=JSON.parse(e.data); if(d.type=='devices'){document.getElementById('count').innerText=d.count; document.getElementById('list').innerText=d.devices.length?d.devices.join(', '):'Nenhum ainda'; log('>> '+e.data)}}
function sendCmd(c){ws.send(JSON.stringify({type:'command',cmd:c})); log('Enviado: '+c)}
function sendUrl(){let u=document.getElementById('url').value; ws.send(JSON.stringify({type:'command',cmd:'open_url',url:u}));}
function log(m){let l=document.getElementById('log'); if(!l){l=document.createElement('div');l.id='log';l.className='box';document.body.appendChild(l)} l.innerHTML=new Date().toLocaleTimeString()+' '+m+'<br>'+l.innerHTML}
</script></body></html>
"""

CLIENT_HTML = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{background:#000;color:#0f0;font-family:monospace;text-align:center;padding:20px}h1{font-size:24px}</style>
</head><body>
<h1>🚜 Fazenda-50 Cliente</h1>
<p id="status">Conectando...</p>
<p id="id"></p>
<script>
let myId = 'cel-'+Math.random().toString(36).substr(2,6);
document.getElementById('id').innerText='ID: '+myId;
let ws = new WebSocket((location.protocol=='https:'?'wss://':'ws://')+location.host+'/ws');
ws.onopen=()=>{ws.send(JSON.stringify({type:'register_client',id:myId})); document.getElementById('status').innerText='✅ CONECTADO - Aguardando comandos';}
ws.onmessage=(e)=>{let d=JSON.parse(e.data); if(d.type=='cmd'){ handleCmd(d); }}
ws.onclose=()=>{document.getElementById('status').innerText='❌ Desconectado, reconectando...'; setTimeout(()=>location.reload(),3000);}
function handleCmd(d){
  document.getElementById('status').innerText='Comando: '+d.cmd;
  if(d.cmd=='open_tiktok'){ window.location.href='https://www.tiktok.com'; }
  if(d.cmd=='open_url' && d.url){ window.location.href=d.url; }
  if(d.cmd=='like'){ /* simula tap no centro */ }
  if(d.cmd=='scroll'){ window.scrollBy(0,300); }
}
</script></body></html>
"""

async def index(request): return web.Response(text=PANEL_HTML, content_type='text/html')
async def client_page(request): return web.Response(text=CLIENT_HTML, content_type='text/html')

async def main():
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_get('/client', client_page)
    app.router.add_get('/ws', lambda r: web.Response(text="use websocket"))
    # websocket server separado
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    
    # servidor websocket na mesma porta com path /ws
    async def ws_app(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        # adaptar para nosso handler simples
        # vamos usar o mesmo dicionario
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("type") == "register_client":
                        dev_id = data.get("id")
                        devices[dev_id] = ws
                        await broadcast_panel()
                    elif data.get("type") == "register_panel":
                        panel_clients.add(ws)
                        await ws.send_str(json.dumps({"type":"devices","devices":list(devices.keys()),"count":len(devices)}))
                    elif data.get("type") == "command":
                        for w in list(devices.values()):
                            try: await w.send_str(json.dumps({"type":"cmd","cmd":data.get("cmd"),"url":data.get("url","")}))
                            except: pass
        finally:
            for k,v in list(devices.items()):
                if v==ws: del devices[k]
            panel_clients.discard(ws)
            await broadcast_panel()
        return ws
    
    app.router.add_get('/ws', ws_app)
    print("Fazenda-50 LIVE")
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
