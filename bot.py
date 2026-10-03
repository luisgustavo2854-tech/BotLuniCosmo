import os
import time
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone
from dotenv import load_dotenv

# Cargar variables del .env
load_dotenv()

COC_TOKEN = os.getenv("COC_TOKEN")
TAG_CLAN = os.getenv("TAG_CLAN", "2R2PJUJ9C").replace("#", "")
ID_INSTANCE = os.getenv("ID_INSTANCE")
API_TOKEN = os.getenv("API_TOKEN")
GREEN_API_URL = os.getenv("GREEN_API_URL", "https://7107.api.greenapi.com/waInstance")
CHAT_ID_GRUPO = os.getenv("CHAT_ID_GRUPO", "") # Se usa para los mensajes autónomos

HEADERS = {
    "Authorization": f"Bearer {COC_TOKEN}",
    "Accept": "application/json"
}

# ==========================================
# 🌐 SERVIDOR WEB FALSO (PARA ENGAÑAR A RENDER)
# ==========================================

class ServidorFalso(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot Luni esta vivo y enganando a Render!")

def mantener_vivo():
    puerto = int(os.environ.get("PORT", 10000))
    httpd = HTTPServer(('0.0.0.0', puerto), ServidorFalso)
    print(f"🌐 Servidor falso escuchando en el puerto {puerto}...")
    httpd.serve_forever()

# ==========================================
# 🧠 MEMORIA DEL VIGILANTE
# ==========================================
ESTADO_GUERRA_ANTERIOR = "desconocido"
ATAQUES_REGISTRADOS = {}
RECORDATORIO_ENVIADO = False
PERFECTA_ANUNCIADA = False
ULTIMA_REVISION = 0
INTERVALO_REVISION = 5 * 60  # Revisa cada 5 minutos

# ==========================================
# 🛠️ FUNCIONES DE SUPERCELL
# ==========================================

def consultar_api_coc(endpoint):
    url = f"https://api.clashofclans.com/v1/{endpoint}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        return res
    except:
        return None

def obtener_datos_guerra():
    clan_tag_hash = f"#{TAG_CLAN}"
    
    res_normal = consultar_api_coc(f"clans/%23{TAG_CLAN}/currentwar")
    if res_normal and res_normal.status_code == 200:
        datos = res_normal.json()
        if datos.get("state") != "notInWar":
            return normalizar_guerra(datos, clan_tag_hash)

    res_liga = consultar_api_coc(f"clans/%23{TAG_CLAN}/currentwar/leaguegroup")
    if res_liga and res_liga.status_code == 200:
        datos_liga = res_liga.json()
        guerra_preparacion, guerra_terminada = None, None

        for ronda in datos_liga.get("rounds", []):
            for war_tag in ronda.get("warTags", []):
                if war_tag == "#0": continue
                res_war = consultar_api_coc(f"clanwarleagues/wars/%23{war_tag.replace('#', '')}")
                if res_war and res_war.status_code == 200:
                    guerra = res_war.json()
                    c_tag, o_tag = guerra.get("clan", {}).get("tag"), guerra.get("opponent", {}).get("tag")

                    if c_tag == clan_tag_hash or o_tag == clan_tag_hash:
                        guerra = normalizar_guerra(guerra, clan_tag_hash)
                        estado = guerra.get("state")
                        if estado == "inWar": return guerra
                        elif estado == "preparation" and not guerra_preparacion: guerra_preparacion = guerra
                        elif estado == "warEnded": guerra_terminada = guerra

        if guerra_preparacion: return guerra_preparacion
        if guerra_terminada: return guerra_terminada

    return {"state": "notInWar"}

def normalizar_guerra(guerra, mi_clan_tag):
    if guerra.get("opponent", {}).get("tag") == mi_clan_tag:
        guerra["clan"], guerra["opponent"] = guerra["opponent"], guerra["clan"]
    return guerra

def calcular_tiempo(fecha_coc):
    try:
        fecha_obj = datetime.strptime(fecha_coc, "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=timezone.utc)
        restante = fecha_obj - datetime.now(timezone.utc)
        if restante.total_seconds() < 0: return "0h 0m"
        horas, resto = divmod(restante.total_seconds(), 3600)
        return f"{int(horas)}h {int(resto // 60)}m"
    except: return "Desconocido"

# ==========================================
# 📊 FUNCIONES DE FORMATO Y ESTRATEGIA (NUEVAS)
# ==========================================

def generar_analisis_th(mi_clan, rival):
    ths_luni, ths_rival = {}, {}
    for m in mi_clan.get("members", []):
        th = m.get("townhallLevel", 0)
        ths_luni[th] = ths_luni.get(th, 0) + 1
    for m in rival.get("members", []):
        th = m.get("townhallLevel", 0)
        ths_rival[th] = ths_rival.get(th, 0) + 1
    todos_ths = sorted(list(set(list(ths_luni.keys()) + list(ths_rival.keys()))), reverse=True)
    lineas = []
    for th in todos_ths:
        c_luni = ths_luni.get(th, 0)
        c_rival = ths_rival.get(th, 0)
        emoji = "🌕" if c_luni >= c_rival else "🌑"
        lineas.append(f"TH{th}: {c_luni} vs {c_rival} {emoji}")
    return "\n".join(lineas)

def generar_limpieza(guerra):
    rivales = sorted(guerra.get("opponent", {}).get("members", []), key=lambda x: x.get("mapPosition", 999))
    lineas = []
    
    for r in rivales:
        mejor_ataque = r.get("bestOpponentAttack")
        if not mejor_ataque:
            lineas.append(f"🎯 #{r.get('mapPosition')} TH{r.get('townhallLevel', '?')} — 0⭐ (Intacto)")
        else:
            estrellas = mejor_ataque.get("stars", 0)
            if estrellas < 3:
                dest = mejor_ataque.get('destructionPercentage', 0)
                dest_str = f"{dest:.2f}%" if dest % 1 != 0 else f"{int(dest)}%"
                lineas.append(f"🎯 #{r.get('mapPosition')} TH{r.get('townhallLevel', '?')} — {estrellas}⭐ ({dest_str})")
    
    if not lineas:
        return "✨ *OPERACIÓN LIMPIEZA* ✨\n\n¡No queda nada por limpiar! Todas las aldeas enemigas han sido destruidas al 100%. 🌟"
        
    msg = "🧹 *OPERACIÓN LIMPIEZA* 🧹\n"
    msg += "Aldeas enemigas que aún se pueden mejorar/cerrar:\n\n"
    msg += "\n".join(lineas)
    return msg

def generar_rival(guerra):
    rival = guerra.get("opponent", {})
    tag = rival.get("tag", "").replace("#", "")
    res = consultar_api_coc(f"clans/%23{tag}")
    
    msg = f"🕵️‍♂️ *RADIOGRAFÍA DEL RIVAL: {rival.get('name')}* 🕵️‍♂️\n\n"
    if res and res.status_code == 200:
        datos = res.json()
        publico = datos.get("isWarLogPublic", False)
        liga = datos.get("warLeague", {}).get("name", "Sin liga")
        
        msg += f"📈 Nivel del Clan: {datos.get('clanLevel', '?')}\n"
        msg += f"🔥 Racha de victorias: {datos.get('warWinStreak', 0)} al hilo\n"
        msg += f"🏆 Liga CWL: {liga}\n\n"
        
        if publico:
            msg += f"📊 Victorias: {datos.get('warWins', 0)} | Derrotas: {datos.get('warLosses', 0)} | Empates: {datos.get('warTies', 0)}\n"
        else:
            msg += f"📊 Victorias: {datos.get('warWins', 0)} | (Historial de derrotas Oculto)\n"
    else:
        msg += "⚠️ No se pudo obtener la información detallada del clan rival."
        
    return msg

def generar_historial():
    res_perfil = consultar_api_coc(f"clans/%23{TAG_CLAN}")
    res_log = consultar_api_coc(f"clans/%23{TAG_CLAN}/warlog")
    
    msg = f"📈 *RENDIMIENTO DE LUNI* 📈\n\n"
    
    if res_perfil and res_perfil.status_code == 200:
        datos_p = res_perfil.json()
        msg += f"🔥 Racha actual: {datos_p.get('warWinStreak', 0)} victorias\n"
        msg += f"⭐ Total de victorias históricas: {datos_p.get('warWins', 0)}\n\n"
        
    if res_log and res_log.status_code == 200:
        datos_l = res_log.json().get("items", [])
        if datos_l:
            msg += "🛡️ Últimas 5 guerras:\n"
            historial = []
            for guerra in datos_l[:5]:
                res = guerra.get("result")
                if res == "win": historial.append("✅")
                elif res == "lose": historial.append("❌")
                elif res == "tie": historial.append("🤝")
                else: historial.append("➖")
            
            msg += " ".join(historial) + "\n"
    else:
        msg += "⚠️ El registro de guerras está inaccesible en este momento."
        
    return msg

def generar_resultados_finales(mi_clan, rival, guerra, terminada=False):
    e_luni, e_rival = mi_clan.get('stars', 0), rival.get('stars', 0)
    d_luni, d_rival = mi_clan.get('destructionPercentage', 0), rival.get('destructionPercentage', 0)
    
    d_luni_str = f"{d_luni:.2f}%" if d_luni % 1 != 0 else f"{int(d_luni)}%"
    d_rival_str = f"{d_rival:.2f}%" if d_rival % 1 != 0 else f"{int(d_rival)}%"

    titulo = "🏁 RESULTADO FINAL DE LA GUERRA" if terminada else "📊 RESULTADO DE LA GUERRA"

    msg = f"{titulo}\n\n"
    msg += f"🏰 {mi_clan.get('name')} — {e_luni} ⭐ • {d_luni_str}\n"
    msg += f"⚔ {rival.get('name')} — {e_rival} ⭐ • {d_rival_str}\n\n"
    
    if terminada:
        ganador = "Empate 🤝"
        if e_luni > e_rival or (e_luni == e_rival and d_luni > d_rival): ganador = f"🎉 {mi_clan.get('name')}"
        elif e_rival > e_luni or (e_rival == e_luni and d_rival > d_luni): ganador = f"💀 {rival.get('name')}"
        msg += f"🏆 GANADOR: {ganador}\n\n"

    msg += "━━━━━━━━━━━━━━━━━\n\n"
    msg += f"👥 ATAQUES DE {mi_clan.get('name').upper()}\n\n"

    membros = sorted(mi_clan.get("members", []), key=lambda x: x.get("mapPosition", 999))
    rival_map = {r.get("tag"): r.get("mapPosition") for r in rival.get("members", [])}

    ataques_registrados = False
    for m in membros:
        ataques_hechos = m.get("attacks", [])
        if not ataques_hechos: continue
        
        ataques_registrados = True
        msg += f"👤 #{m.get('mapPosition')} {m.get('name')}\n"
        for atk in ataques_hechos:
            def_pos = rival_map.get(atk.get("defenderTag"), "?")
            estrellas = atk.get("stars", 0)
            stars_str = "⭐" * estrellas if estrellas > 0 else "0 ⭐"
            dest = atk.get("destructionPercentage", 0)
            dest_str = f"{dest:.2f}%" if dest % 1 != 0 else f"{int(dest)}%"
            msg += f"🎯 #{def_pos} • {stars_str} • {dest_str}\n"
        msg += "\n"

    if not ataques_registrados: msg += "Aún no hay ataques registrados en esta guerra."
    return msg.strip()

def generar_podio(mi_clan, titulo="🏆 *TOP 5 MVP - {clan}* 🏆"):
    membros = mi_clan.get("members", [])
    atacantes = []
    
    for m in membros:
        ataques = m.get("attacks", [])
        if ataques:
            estrellas = sum(atk.get("stars", 0) for atk in ataques)
            destruccion = sum(atk.get("destructionPercentage", 0) for atk in ataques)
            duracion = sum(atk.get("duration", 0) for atk in ataques) 
            atacantes.append({"nombre": m.get("name"), "estrellas": estrellas, "destruccion": destruccion, "duracion": duracion})
            
    if not atacantes: return "🌙 Aún no hay ataques registrados para armar el podio."
        
    atacantes_ordenados = sorted(atacantes, key=lambda x: (x["estrellas"], x["destruccion"], -x["duracion"]), reverse=True)
    top5 = atacantes_ordenados[:5]
    
    msg = titulo.format(clan=mi_clan.get('name').upper()) + "\n━━━━━━━━━━━━━━━━━\n\n"
    
    for i, atk in enumerate(top5):
        medalla = ["🥇", "🥈", "🥉", "🏅", "🏅"][i] if i < 5 else "🏅"
        dest_str = f"{atk['destruccion']:.2f}%" if atk['destruccion'] % 1 != 0 else f"{int(atk['destruccion'])}%"
        mins, segs = divmod(atk['duracion'], 60)
        msg += f"{medalla} {atk['nombre']}\n   ↳ {atk['estrellas']} ⭐ • {dest_str} • ⏱️ {mins}m {segs}s\n\n"

    return msg.strip()

def generar_mensaje_pendientes(guerra, es_automatico=True):
    mi_clan, rival = guerra.get("clan", {}), guerra.get("opponent", {})
    titulo = "⏰ *¡ATENCIÓN! ÚLTIMAS HORAS DE GUERRA* ⏰" if es_automatico else "📋 *REPORTE DE ATAQUES PENDIENTES* 📋"
    ataques_permitidos = guerra.get("attacksPerMember", 2)
    
    msg = f"{titulo}\n\n🏆 Pendientes\n🏟️ {'Liga de Guerras' if ataques_permitidos == 1 else 'Guerra de Clanes'}\n"
    msg += f"⭐ Equipo: {mi_clan.get('stars', 0)} | Rival: {rival.get('stars', 0)}\n"
    msg += f"⏰ Tiempo: {calcular_tiempo(guerra.get('endTime'))}\n\n⚔️ Faltan por atacar:\n\n"
    
    membros = sorted(mi_clan.get("members", []), key=lambda x: x.get("mapPosition", 999))
    todos_atacaron = True
    
    for m in membros:
        faltan = ataques_permitidos - len(m.get("attacks", []))
        if faltan > 0:
            todos_atacaron = False
            emoji = "🌕" if faltan == 2 or ataques_permitidos == 1 else "🌗"
            msg += f"#{m.get('mapPosition')} {m.get('name')} | {faltan}{emoji}\n"
            
    if todos_atacaron: msg += "¡Todo el clan ha hecho sus ataques! 🎉\n"
    return msg.strip()

# ==========================================
# 📱 FUNCIONES DE WHATSAPP
# ==========================================

def enviar_whatsapp(chat_id, mensaje):
    url = f"{GREEN_API_URL}{ID_INSTANCE}/sendMessage/{API_TOKEN}"
    requests.post(url, json={"chatId": chat_id, "message": mensaje})

def borrar_notificacion(receipt_id):
    requests.delete(f"{GREEN_API_URL}{ID_INSTANCE}/deleteNotification/{API_TOKEN}/{receipt_id}")

def enviar_autonomo(mensaje):
    if CHAT_ID_GRUPO: enviar_whatsapp(CHAT_ID_GRUPO, mensaje)

# ==========================================
# 🤖 EL VIGILANTE (EVENTOS AUTÓNOMOS)
# ==========================================

def verificar_cambios_guerra():
    global ESTADO_GUERRA_ANTERIOR, ATAQUES_REGISTRADOS, RECORDATORIO_ENVIADO, PERFECTA_ANUNCIADA
    
    guerra = obtener_datos_guerra()
    estado_actual = guerra.get("state")
    if not estado_actual: return

    mi_clan, rival = guerra.get("clan", {}), guerra.get("opponent", {})

    if ESTADO_GUERRA_ANTERIOR == "desconocido":
        ESTADO_GUERRA_ANTERIOR = estado_actual
        if estado_actual == "inWar":
            for m in mi_clan.get("members", []):
                ATAQUES_REGISTRADOS[m.get("tag")] = len(m.get("attacks", []))
        return

    # EVENTO 1: Inicia Preparación
    if ESTADO_GUERRA_ANTERIOR != "preparation" and estado_actual == "preparation":
        enviar_autonomo(f"🔎 *¡NUEVA GUERRA ENCONTRADA!*\nLuni ha entrado en fase de preparación contra {rival.get('name')}.")
        # AUTOMATIZACIÓN RIVAL:
        enviar_autonomo(generar_rival(guerra))
        
        ATAQUES_REGISTRADOS.clear()
        RECORDATORIO_ENVIADO, PERFECTA_ANUNCIADA = False, False

    # EVENTO 2: Inicia Guerra
    elif ESTADO_GUERRA_ANTERIOR != "inWar" and estado_actual == "inWar":
        msg_inicio = (f"🔥 *¡LA GUERRA HA COMENZADO!* 🔥\n\n🌕 {mi_clan.get('name')}\n🌑 vs {rival.get('name')}\n\n"
                      f"⏱️ Termina en: {calcular_tiempo(guerra.get('endTime'))}\n────────────────\n"
                      f"✨ Análisis Estelar (Balance por TH)\n\n{generar_analisis_th(mi_clan, rival)}\n\n🌙 ¡Que la Luna guíe sus ataques!")
        enviar_autonomo(msg_inicio)
        
        ATAQUES_REGISTRADOS.clear()
        RECORDATORIO_ENVIADO, PERFECTA_ANUNCIADA = False, False
        for m in mi_clan.get("members", []): ATAQUES_REGISTRADOS[m.get("tag")] = len(m.get("attacks", []))

    # EVENTO 3: Finaliza Guerra
    elif ESTADO_GUERRA_ANTERIOR == "inWar" and estado_actual in ["warEnded", "notInWar"]:
        enviar_autonomo(generar_resultados_finales(mi_clan, rival, guerra, terminada=True))
        enviar_autonomo(generar_podio(mi_clan, titulo="🏆 *TOP 5 FINAL DEL DÍA - {clan}* 🏆"))
        
        # AUTOMATIZACIÓN HISTORIAL (Solo en guerra normal, es decir 2 ataques)
        if guerra.get("attacksPerMember", 2) == 2:
            enviar_autonomo(generar_historial())
            
        ATAQUES_REGISTRADOS.clear()

    ESTADO_GUERRA_ANTERIOR = estado_actual

    # EVENTOS DURANTE LA GUERRA (Ataques y Recordatorios)
    if estado_actual == "inWar":
        for m in mi_clan.get("members", []):
            tag = m.get("tag")
            ataques = m.get("attacks", [])
            act_len = len(ataques)
            ant_len = ATAQUES_REGISTRADOS.get(tag, -1)

            if ant_len != -1 and act_len > ant_len:
                ultimo = ataques[-1]
                defensor = next((r for r in rival.get("members", []) if r.get("tag") == ultimo.get("defenderTag")), {})
                mins, segs = divmod(ultimo.get("duration", 0), 60)
                
                estrellas = ultimo.get('stars', 0)
                stars_str = "⭐" * estrellas if estrellas > 0 else "0 ⭐"
                dest = ultimo.get('destructionPercentage', 0)
                dest_str = f"{dest:.2f}%" if dest % 1 != 0 else f"{int(dest)}%"
                
                msg_atk = (f"⚔️ NUEVO ATAQUE DE {mi_clan.get('name').upper()}\n\n"
                           f"👤 #{m.get('mapPosition')} {m.get('name')}\n"
                           f"🎯 #{defensor.get('mapPosition', '?')} {defensor.get('name', 'Desconocido')} • {stars_str} • {dest_str}\n"
                           f"⏱️ {mins}m {segs}s")
                enviar_autonomo(msg_atk)
            
            ATAQUES_REGISTRADOS[tag] = act_len

        max_estrellas = guerra.get("teamSize", 0) * 3
        if mi_clan.get('stars', 0) == max_estrellas and max_estrellas > 0 and not PERFECTA_ANUNCIADA:
            enviar_autonomo("🌟 *¡GUERRA PERFECTA ALCANZADA!* 🌟\nEl clan logró todas las estrellas posibles.")
            PERFECTA_ANUNCIADA = True

        # EVENTO 4: Recordatorio 5 Horas
        if guerra.get("endTime") and not RECORDATORIO_ENVIADO:
            try:
                f_obj = datetime.strptime(guerra["endTime"], "%Y%m%dT%H%M%S.%fZ").replace(tzinfo=timezone.utc)
                restante = (f_obj - datetime.now(timezone.utc)).total_seconds()
                
                if 0 < restante <= 18000: # Quedan 5 horas o menos
                    if mi_clan.get('stars', 0) < max_estrellas:
                        enviar_autonomo(generar_mensaje_pendientes(guerra, es_automatico=True))
                        # AUTOMATIZACIÓN LIMPIEZA:
                        enviar_autonomo(generar_limpieza(guerra))
                    RECORDATORIO_ENVIADO = True
            except: pass

# ==========================================
# 🎮 COMANDOS
# ==========================================

def cmd_time():
    guerra = obtener_datos_guerra()
    if guerra.get("state") == "notInWar": return "🌙 Luni no está en guerra."
    if guerra.get("state") == "warEnded": return "🌙 La guerra terminó."
    fase = "⏳ La guerra *COMIENZA* en:" if guerra.get("state") == "preparation" else "⏰ La guerra *TERMINA* en:"
    return f"⏳ *REPORTE DE TIEMPO* ⏳\n\n⚔️ *{guerra.get('clan', {}).get('name')}* vs *{guerra.get('opponent', {}).get('name')}*\n\n{fase} {calcular_tiempo(guerra.get('startTime' if guerra.get('state') == 'preparation' else 'endTime'))}"

def cmd_guerra():
    guerra = obtener_datos_guerra()
    estado = guerra.get("state")
    if estado == "notInWar": return "🌙 No hay guerra activa."
    
    mi_clan, rival = guerra.get("clan", {}), guerra.get("opponent", {})
    analisis_th = generar_analisis_th(mi_clan, rival)
    
    if estado == "preparation":
        return (f"⏳ *FASE DE PREPARACIÓN* ⏳\n\n⚔️ *{mi_clan.get('name')}* vs *{rival.get('name')}*\n\n"
               f"⏳ La batalla *COMIENZA* en: *{calcular_tiempo(guerra.get('startTime'))}*\n────────────────\n"
               f"✨ Balance de Ayuntamientos (TH)\n\n{analisis_th}\n\n¡Preparen sus aldeas!")
    
    return (f"🔥 *ESTADO DE LA GUERRA* 🔥\n\n🏰 *{mi_clan.get('name')}*: {mi_clan.get('stars', 0)} ⭐ ({mi_clan.get('destructionPercentage', 0):.2f}%)\n"
           f"🆚\n🏰 *{rival.get('name')}*: {rival.get('stars', 0)} ⭐ ({rival.get('destructionPercentage', 0):.2f}%)\n"
           f"────────────────\n✨ Balance de Ayuntamientos (TH)\n\n{analisis_th}\n\n⚔️ Usa !resultados para ver el detalle.")

def cmd_resultados():
    guerra = obtener_datos_guerra()
    estado = guerra.get("state")
    if estado == "notInWar": return "🌙 No hay guerra activa."
    if estado == "preparation": return "🌙 La guerra está en fase de *Preparación*. Aún no hay ataques."
    return generar_resultados_finales(guerra.get("clan", {}), guerra.get("opponent", {}), guerra, terminada=False)

def cmd_ataques():
    guerra = obtener_datos_guerra()
    estado = guerra.get("state")
    if estado == "notInWar": return "🌙 No hay guerra activa."
    if estado == "preparation": return "🌙 La guerra está en fase de *Preparación*. Todos los ataques están pendientes."
    return generar_mensaje_pendientes(guerra, es_automatico=False)

def cmd_podio():
    guerra = obtener_datos_guerra()
    estado = guerra.get("state")
    if estado == "notInWar": return "🌙 No hay guerra activa."
    if estado == "preparation": return "🌙 La guerra está en preparación. ¡Aún no hay ataques para el podio!"
    return generar_podio(guerra.get("clan", {}))

# NUEVOS COMANDOS TÁCTICOS
def cmd_limpieza():
    guerra = obtener_datos_guerra()
    if guerra.get("state") == "notInWar": return "🌙 No hay guerra activa."
    if guerra.get("state") == "preparation": return "🌙 La guerra aún no comienza."
    return generar_limpieza(guerra)

def cmd_rival():
    guerra = obtener_datos_guerra()
    if guerra.get("state") == "notInWar": return "🌙 No hay guerra activa."
    return generar_rival(guerra)

def cmd_historial():
    return generar_historial()

# ==========================================
# 🚀 BUCLE PRINCIPAL
# ==========================================

def procesar_mensajes():
    global ULTIMA_REVISION
    print("🤖 Bot Luni (Python) operando limpio y en local/nube...")
    while True:
        ahora = time.time()
        if ahora - ULTIMA_REVISION > INTERVALO_REVISION:
            verificar_cambios_guerra()
            ULTIMA_REVISION = ahora

        url = f"{GREEN_API_URL}{ID_INSTANCE}/receiveNotification/{API_TOKEN}"
        try:
            res = requests.get(url, timeout=20)
            if res.status_code == 200 and res.json():
                datos = res.json()
                receipt_id = datos.get("receiptId")
                body = datos.get("body", {})

                if body.get("typeWebhook") in ["incomingMessageReceived", "outgoingMessageReceived"]:
                    chat_id = body.get("senderData", {}).get("chatId")
                    msg_data = body.get("messageData", {})
                    tipo_msg = msg_data.get("typeMessage", "")
                    
                    texto = ""
                    if tipo_msg == "textMessage": texto = msg_data.get("textMessageData", {}).get("textMessage", "")
                    elif tipo_msg == "extendedTextMessage": texto = msg_data.get("extendedTextMessageData", {}).get("text", "")

                    comando = texto.strip().lower()
                    if comando:
                        print(f"➤ Comando leído: {comando}")
                        if comando in ["!time", "!tiempo"]: enviar_whatsapp(chat_id, cmd_time())
                        elif comando == "!guerra": enviar_whatsapp(chat_id, cmd_guerra())
                        elif comando == "!resultados": enviar_whatsapp(chat_id, cmd_resultados())
                        elif comando == "!ataques": enviar_whatsapp(chat_id, cmd_ataques())
                        elif comando == "!podio": enviar_whatsapp(chat_id, cmd_podio())
                        
                        # NUEVOS COMANDOS TÁCTICOS
                        elif comando == "!limpieza": enviar_whatsapp(chat_id, cmd_limpieza())
                        elif comando == "!rival": enviar_whatsapp(chat_id, cmd_rival())
                        elif comando == "!historial": enviar_whatsapp(chat_id, cmd_historial())
                        
                        elif comando == "!ip": enviar_whatsapp(chat_id, f"🌐 Mi IP local es: {requests.get('https://api.ipify.org').text}")
                        elif comando.startswith("!token "):
                            nuevo_token = texto.replace("!token ", "").strip()
                            HEADERS["Authorization"] = f"Bearer {nuevo_token}"
                            enviar_whatsapp(chat_id, "✅ Token de Supercell actualizado en caliente. Luni está listo para la guerra.")

                borrar_notificacion(receipt_id)

        except requests.exceptions.RequestException: pass 
        except Exception as e: print(f"⚠️ Error general: {e}")
        
        time.sleep(3) 

if __name__ == "__main__":
    threading.Thread(target=mantener_vivo, daemon=True).start()
    procesar_mensajes()
