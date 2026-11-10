import asyncio
import json
import os
import logging
from aiohttp import web

logging.basicConfig(level=logging.INFO)
devices = {}
admin_clients = set()

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    device_id = None
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except:
                    continue
                t = data.get('type')
                
                if t == 'register':
                    device_id = data.get('id', f'dev-{len(devices)}')
                    devices[device_id] = {'ws': ws, 'status': 'online', 'info': data}
                    logging.info(f"Device connected: {device_id}")
                    await broadcast_admin()
                
                elif t == 'admin_join':
                    admin_clients.add(ws)
                    await ws.send_str(json.dumps({'type': 'devices', 'devices': list(devices.keys()), 'count': len(devices)}))
                
                elif t == 'command':
                    target = data.get('target', 'all')
                    cmd = data.get('command')
                    payload = data.get('payload')
                    sent = 0
                    if target == 'all':
                        for d in list(devices.values()):
                            try:
                                await d['ws'].send_str(json.dumps({'type': 'cmd', 'command': cmd, 'payload': payload}))
                                sent += 1
                            except:
                                pass
                    await ws.send_str(json.dumps({'type': 'ok', 'sent': sent}))
                
                elif t in ['status', 'heartbeat']:
                    if device_id in devices:
                        devices[device_id]['last'] = data

            elif msg.type == web.WSMsgType.ERROR:
                break
    except Exception as e:
        logging.error(f"WS error: {e}")
    finally:
        if device_id and device_id in devices:
            del devices[device_id]
            logging.info(f"Device disconnected: {device_id}")
            await broadcast_admin()
        if ws in admin_clients:
            admin_clients.remove(ws)
    return ws

async def broadcast_admin():
    msg = json.dumps({'type': 'devices', 'devices': list(devices.keys()), 'count': len(devices)})
    for ac in list(admin_clients):
        try:
            await ac.send_str(msg)
        except:
            pass

async def index_handler(request):
    html = """
<!DOCTYPE html>
<html><head><title>Fazenda-50 Painel</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#0f0f0f;color:#0f0;font-family:monospace;padding:20px}
.card{border:1px solid #0f0;padding:15px;margin:10px 0;border-radius:8px}
button{background:#0f0;color:#000;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;margin:5px}
input{padding:8px;border-radius:5px;border:1px solid #0f0;background:#000;color:#0f0}
#log{height:200px;overflow:auto;background:#000;font-size:12px}
</style></head><body>
<h1>🚜 Fazenda-50 is LIVE</h1>
<div class="card">Server: fazenda-50.onrender.com<br>Status: <span style="color:lime">ONLINE</span><br>Dispositivos conectados: <b id="count">0</b></div>
<div class="card"><h3>Lista de Celulares</h3><div id="list">Nenhum ainda</div></div>
<div class="card">
<h3>Comandos</h3>
<button onclick="sendCmd('open_tiktok')">Abrir TikTok</button>
<button onclick="sendCmd('like')">Dar Like</button>
<button onclick="sendCmd('follow')">Seguir</button>
<button onclick="sendCmd('scroll')">Rolar</button><br><br>
<input id="customUrl" placeholder="URL / comando" style="width:60%"><button onclick="sendCustom()">Enviar URL</button>
</div>
<div id="log" class="card"></div>
<script>
let ws = new WebSocket((location.protocol=='https:'?'wss://':'ws://')+location.host+'/ws');
ws.onopen=()=>{log('Conectado ao painel'); ws.send(JSON.stringify({type:'admin_join'}))};
ws.onmessage=(e)=>{let d=JSON.parse(e.data); if(d.type=='devices'){document.getElementById('count').innerText=d.count; document.getElementById('list').innerHTML=d.devices.length?d.devices.map(x=>'<div>📱 '+x+'</div>').join(''):'Nenhum ainda'} log('>> '+e.data)};
ws.onclose=()=>{log('Desconectado, recarregando em 3s...'); setTimeout(()=>location.reload(),3000)};
function log(m){let el=document.getElementById('log'); el.innerHTML+='<div>'+new Date().toLocaleTimeString()+' '+m+'</div>'; el.scrollTop=el.scrollHeight}
function sendCmd(c){ws.send(JSON.stringify({type:'command', target:'all', command:c})); log('Enviado: '+c)}
function sendCustom(){let v=document.getElementById('customUrl').value; if(!v)return; ws.send(JSON.stringify({type:'command', target:'all', command:'open_url', payload:v})); log('Enviado URL: '+v)}
</script></body></html>
"""
    return web.Response(text=html, content_type='text/html')

app = web.Application()
app.router.add_get('/', index_handler)
app.router.add_get('/ws', websocket_handler)
app.router.add_get('/health', lambda r: web.Response(text="OK"))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    web.run_app(app, host='0.0.0.0', port=port)
