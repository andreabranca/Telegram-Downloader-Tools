#!/usr/bin/env python3
import argparse
import asyncio
import os
import pandas as pd
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError

def parse_args():
    p = argparse.ArgumentParser(description="Baixa vídeos do Telegram por múltiplas hashtags")
    p.add_argument("--api-id", type=int, required=True, help="API ID (my.telegram.org)")
    p.add_argument("--api-hash", type=str, required=True, help="API HASH (my.telegram.org)")
    p.add_argument("--target", required=True, help="Canal ou grupo (ex: https://t.me/nomeCanal ou @nomeCanal)")
    p.add_argument("--tags", required=True, help='Lista de hashtags separadas por vírgula (ex: "#299,#300,#promo")')
    p.add_argument("--out", default="./downloads", help="Pasta de saída")
    p.add_argument("--limit", type=int, default=0, help="Limite de mensagens por tag (0 = sem limite)")
    p.add_argument("--session", default="session", help="Nome do arquivo de sessão Telethon")
    p.add_argument("--max-flood-wait", type=int, default=300, help="Tempo máximo (em segundos) de FloodWait automático antes de abortar (padrão: 300s)")
    return p.parse_args()

def safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in s).strip()

import time

# Variável global para armazenar o tempo do último progresso
last_progress_time = time.time()
last_progress_bytes = 0

def progress_callback(current, total):
    """Callback para mostrar progresso do download"""
    global last_progress_time, last_progress_bytes
    
    if total > 0:
        # Calcular velocidade
        current_time = time.time()
        time_diff = current_time - last_progress_time
        bytes_diff = current - last_progress_bytes
        
        if time_diff > 0:  # Evitar divisão por zero
            speed = bytes_diff / time_diff  # bytes por segundo
            speed_mb = speed / (1024 * 1024)  # converter para MB/s
        else:
            speed_mb = 0
            
        # Atualizar valores para próximo cálculo
        last_progress_time = current_time
        last_progress_bytes = current
        
        # Calcular porcentagem e barra de progresso
        percent = (current / total) * 100
        bar_length = 40
        filled = int(bar_length * current / total)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        # Formatar tamanhos
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        
        # Calcular tempo estimado restante (ETA)
        if speed > 0:
            bytes_remaining = total - current
            eta_seconds = bytes_remaining / speed
            eta_min = int(eta_seconds // 60)
            eta_sec = int(eta_seconds % 60)
            eta_str = f"ETA: {eta_min}m{eta_sec}s"
        else:
            eta_str = "ETA: --"
        
        print(f'\r⬇️  [{bar}] {percent:.1f}% ({current_mb:.1f}/{total_mb:.1f} MB) - {speed_mb:.1f} MB/s - {eta_str}', 
            end='', flush=True)

async def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)
    
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if not tags:
        raise SystemExit("Nenhuma tag válida informada (use ex: --tags \"#299,#300\").")
    
    client = TelegramClient(args.session, args.api_id, args.api_hash)
    await client.start()
    print(f"Conectado como: {(await client.get_me()).username}")
    
    csv_path = os.path.join(args.out, "videos_baixados.csv")
    registros = []
    total_baixados = 0
    total_encontrados = 0
    
    for tag in tags:
        print(f"\n🔍 Procurando vídeos com a tag: {tag}")
        count_tag = 0

        # Resolver a entidade do target uma vez, tentando novamente se houver FloodWait
        while True:
            try:
                entity = await client.get_input_entity(args.target)
                break
            except FloodWaitError as e:
                # Telethon exige aguardar; se o tempo for muito grande, abortar com instrução
                print(f"\n⏳ Flood wait ao resolver target ({e.seconds}s)")
                if e.seconds > args.max_flood_wait:
                    raise SystemExit(
                        f"Flood wait muito longo ({e.seconds}s) ao resolver target. "
                        f"Recomendo aguardar manualmente ou rodar novamente com --max-flood-wait {e.seconds} "
                        "se quiser que o script espere esse tempo automaticamente."
                    )
                print(f"→ Aguardando {e.seconds}s (máx automático: {args.max_flood_wait}s)")
                await asyncio.sleep(e.seconds + 1)

        # Iterar mensagens; se ocorrer FloodWait durante a iteração, aguardar e reiniciar
        # Usar um conjunto para evitar reprocessar mensagens já vistas se precisarmos reiniciar a iteração
        seen_msg_ids = set()
        while True:
            try:
                async for msg in client.iter_messages(entity, search=tag, limit=(args.limit or None)):
                    if msg.id in seen_msg_ids:
                        continue
                    seen_msg_ids.add(msg.id)
                    total_encontrados += 1

                    if not msg.message or tag not in msg.message:
                        continue
                    if not msg.media:
                        continue

                    is_video = getattr(msg, "video", None) is not None
                    mime = getattr(msg.media, "mime_type", "") if msg.media else ""
                    if not is_video and not mime.startswith("video"):
                        continue

                    # Extrair nome do vídeo da última linha da mensagem
                    lines = [l.strip() for l in msg.message.split('\n') if l.strip()]
                    video_name = lines[-1] if lines else f"msg{msg.id}"

                    # Remover prefixos como "===" , "==", "=" do início
                    while video_name.startswith('='):
                        video_name = video_name[1:].strip()

                    # Nome do arquivo
                    date_str = msg.date.strftime("%Y%m%d_%H%M%S") if msg.date else "nodate"
                    filename = safe_filename(video_name) + ".mp4"
                    out_path = os.path.join(args.out, filename)

                    if os.path.exists(out_path):
                        print(f"⏩ Já existe: {filename}")
                        continue

                    try:
                        print(f"\n⏬ Baixando: {filename}")
                        # Resetar variáveis globais antes de cada download
                        global last_progress_time, last_progress_bytes
                        last_progress_time = time.time()
                        last_progress_bytes = 0

                        await client.download_media(msg, file=out_path, progress_callback=progress_callback)
                        print()  # Nova linha após completar o download

                        total_baixados += 1
                        count_tag += 1

                        registros.append({
                            "tag": tag,
                            "msg_id": msg.id,
                            "data": msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else "",
                            "arquivo": filename,
                            "legenda": msg.message or "",
                        })

                    except FloodWaitError as e:
                        print(f"\n⏳ Flood wait ({e.seconds}s) → aguardando...")
                        await asyncio.sleep(e.seconds + 1)
                    except Exception as e:
                        print(f"\n Erro ao baixar msg {msg.id}: {e}")
                # se o async for terminou sem FloodWait, encerrar o while
                break
            except FloodWaitError as e:
                print(f"\n⏳ Flood wait durante iteração ({e.seconds}s)")
                if e.seconds > args.max_flood_wait:
                    raise SystemExit(
                        f"Flood wait muito longo ({e.seconds}s) durante iteração. "
                        f"Rode novamente com --max-flood-wait {e.seconds} para aceitar essa espera automática, "
                        "ou aguarde manualmente e tente novamente mais tarde."
                    )
                print(f"→ Aguardando {e.seconds}s (máx automático: {args.max_flood_wait}s) e reiniciando...")
                await asyncio.sleep(e.seconds + 1)
        
        print(f"✅ Tag {tag}: {count_tag} vídeos baixados.")
    
    await client.disconnect()
    
    if registros:
        df = pd.DataFrame(registros)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n📄 CSV salvo em: {csv_path}")
    
    print(f"\n🚀 Finalizado: {total_baixados} vídeos baixados ({total_encontrados} mensagens verificadas).")

if __name__ == "__main__":
    asyncio.run(main())