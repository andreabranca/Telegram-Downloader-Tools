#!/usr/bin/env python3
import asyncio
import os
import pandas as pd
import threading
import time
import json
from datetime import datetime
from telethon import TelegramClient
from telethon.errors import FloodWaitError
import customtkinter as ctk
from tkinter import filedialog, scrolledtext, messagebox
import sys

# Configuração do CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in s).strip()


class TelegramDownloaderGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Telegram Video Downloader")
        self.root.geometry("900x800")

        # Variáveis para controle de download
        self.downloading = False
        self.last_progress_time = time.time()
        self.last_progress_bytes = 0

        self.create_widgets()

    def create_widgets(self):
        # Frame principal com scroll
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Título
        title_label = ctk.CTkLabel(
            main_frame,
            text="Telegram Video Downloader",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.pack(pady=(10, 20))

        # Frame para inputs
        input_frame = ctk.CTkFrame(main_frame)
        input_frame.pack(fill="x", padx=10, pady=5)

        # API ID
        ctk.CTkLabel(input_frame, text="API ID:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=5
        )
        self.api_id_entry = ctk.CTkEntry(
            input_frame, width=300, placeholder_text="Digite seu API ID"
        )
        self.api_id_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        # API Hash
        ctk.CTkLabel(
            input_frame, text="API Hash:", font=ctk.CTkFont(weight="bold")
        ).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.api_hash_entry = ctk.CTkEntry(
            input_frame, width=300, placeholder_text="Digite seu API Hash", show="*"
        )
        self.api_hash_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # Target (Canal/Grupo)
        ctk.CTkLabel(
            input_frame, text="Canal/Grupo:", font=ctk.CTkFont(weight="bold")
        ).grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.target_entry = ctk.CTkEntry(
            input_frame, width=300, placeholder_text="@nome ou https://t.me/nome"
        )
        self.target_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # Tags
        ctk.CTkLabel(input_frame, text="Tags:", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, sticky="w", padx=10, pady=5
        )
        self.tags_entry = ctk.CTkEntry(
            input_frame, width=300, placeholder_text="#tag1,#tag2,#tag3"
        )
        self.tags_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        # Pasta de saída
        output_frame = ctk.CTkFrame(input_frame)
        output_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(
            output_frame, text="Pasta de saída:", font=ctk.CTkFont(weight="bold")
        ).pack(side="left", padx=(0, 10))
        self.output_entry = ctk.CTkEntry(
            output_frame, width=350, placeholder_text="./downloads"
        )
        self.output_entry.insert(0, "./downloads")
        self.output_entry.pack(side="left", padx=5, fill="x", expand=True)

        browse_btn = ctk.CTkButton(
            output_frame, text="Procurar", width=100, command=self.browse_folder
        )
        browse_btn.pack(side="left", padx=5)

        # Limite de mensagens
        ctk.CTkLabel(
            input_frame, text="Limite por tag:", font=ctk.CTkFont(weight="bold")
        ).grid(row=5, column=0, sticky="w", padx=10, pady=5)
        self.limit_entry = ctk.CTkEntry(
            input_frame, width=300, placeholder_text="0 = sem limite"
        )
        self.limit_entry.insert(0, "0")
        self.limit_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        # Nome da sessão
        ctk.CTkLabel(
            input_frame, text="Nome da sessão:", font=ctk.CTkFont(weight="bold")
        ).grid(row=6, column=0, sticky="w", padx=10, pady=5)
        self.session_entry = ctk.CTkEntry(
            input_frame, width=300, placeholder_text="session"
        )
        self.session_entry.insert(0, "session")
        self.session_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        # Max flood wait
        ctk.CTkLabel(
            input_frame, text="Max Flood Wait (s):", font=ctk.CTkFont(weight="bold")
        ).grid(row=7, column=0, sticky="w", padx=10, pady=5)
        self.max_flood_entry = ctk.CTkEntry(
            input_frame, width=300, placeholder_text="300"
        )
        self.max_flood_entry.insert(0, "300")
        self.max_flood_entry.grid(row=7, column=1, padx=10, pady=5, sticky="ew")

        input_frame.columnconfigure(1, weight=1)

        # Frame para botões de configuração
        config_btn_frame = ctk.CTkFrame(main_frame)
        config_btn_frame.pack(fill="x", padx=10, pady=5)

        save_config_btn = ctk.CTkButton(
            config_btn_frame,
            text="Salvar Configuração",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35,
            command=self.save_config,
            fg_color="green",
            hover_color="darkgreen",
        )
        save_config_btn.pack(side="left", padx=5, fill="x", expand=True)

        load_config_btn = ctk.CTkButton(
            config_btn_frame,
            text="Carregar Configuração",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35,
            command=self.load_config,
            fg_color="orange",
            hover_color="darkorange",
        )
        load_config_btn.pack(side="left", padx=5, fill="x", expand=True)

        # Botão de download
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", padx=10, pady=10)

        self.download_btn = ctk.CTkButton(
            btn_frame,
            text="Iniciar Download",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40,
            command=self.start_download,
        )
        self.download_btn.pack(side="left", padx=5, fill="x", expand=True)

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="Parar",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40,
            fg_color="red",
            hover_color="darkred",
            command=self.stop_download,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=5, fill="x", expand=True)

        # Barra de progresso
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            progress_frame, text="Progresso:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(5, 0))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame, text="Aguardando...", font=ctk.CTkFont(size=12)
        )
        self.progress_label.pack(anchor="w", padx=10, pady=(0, 5))

        # Área de log
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(log_frame, text="Log:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(5, 0)
        )

        self.log_text = ctk.CTkTextbox(
            log_frame, wrap="word", height=250, font=ctk.CTkFont(size=11)
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)

    def log(self, message):
        """Adiciona mensagem ao log"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.root.update_idletasks()

    def progress_callback(self, current, total):
        """Callback para mostrar progresso do download"""
        if total > 0:
            # Calcular velocidade
            current_time = time.time()
            time_diff = current_time - self.last_progress_time
            bytes_diff = current - self.last_progress_bytes

            if time_diff > 0:
                speed = bytes_diff / time_diff
                speed_mb = speed / (1024 * 1024)
            else:
                speed_mb = 0

            self.last_progress_time = current_time
            self.last_progress_bytes = current

            # Atualizar barra de progresso
            percent = current / total
            self.progress_bar.set(percent)

            # Formatar tamanhos
            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)

            # Calcular ETA
            if speed > 0:
                bytes_remaining = total - current
                eta_seconds = bytes_remaining / speed
                eta_min = int(eta_seconds // 60)
                eta_sec = int(eta_seconds % 60)
                eta_str = f"ETA: {eta_min}m{eta_sec}s"
            else:
                eta_str = "ETA: --"

            # Atualizar label
            progress_text = f"{percent * 100:.1f}% ({current_mb:.1f}/{total_mb:.1f} MB) - {speed_mb:.1f} MB/s - {eta_str}"
            self.progress_label.configure(text=progress_text)

    def validate_inputs(self):
        """Valida os campos de entrada"""
        if not self.api_id_entry.get().strip():
            self.log("❌ Erro: API ID é obrigatório!")
            return False

        if not self.api_hash_entry.get().strip():
            self.log("❌ Erro: API Hash é obrigatório!")
            return False

        if not self.target_entry.get().strip():
            self.log("❌ Erro: Canal/Grupo é obrigatório!")
            return False

        if not self.tags_entry.get().strip():
            self.log("❌ Erro: Tags são obrigatórias!")
            return False

        try:
            int(self.api_id_entry.get().strip())
        except ValueError:
            self.log("❌ Erro: API ID deve ser um número!")
            return False

        try:
            int(self.limit_entry.get().strip())
        except ValueError:
            self.log("❌ Erro: Limite deve ser um número!")
            return False

        try:
            int(self.max_flood_entry.get().strip())
        except ValueError:
            self.log("❌ Erro: Max Flood Wait deve ser um número!")
            return False

        return True

    def start_download(self):
        """Inicia o processo de download"""
        if not self.validate_inputs():
            return

        self.downloading = True
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Iniciando...")

        # Executar download em thread separada
        thread = threading.Thread(target=self.run_download, daemon=True)
        thread.start()

    def stop_download(self):
        """Para o processo de download"""
        self.downloading = False
        self.log("⏹ Parando download...")
        self.download_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def run_download(self):
        """Executa o download de forma assíncrona"""
        try:
            # Criar novo event loop para esta thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.download_videos())
        except Exception as e:
            self.log(f"❌ Erro fatal: {e}")
        finally:
            self.download_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.downloading = False

    async def download_videos(self):
        """Função principal de download"""
        # Obter parâmetros
        api_id = int(self.api_id_entry.get().strip())
        api_hash = self.api_hash_entry.get().strip()
        target = self.target_entry.get().strip()
        tags_str = self.tags_entry.get().strip()
        out_path = self.output_entry.get().strip()
        limit = int(self.limit_entry.get().strip())
        session = self.session_entry.get().strip()
        max_flood_wait = int(self.max_flood_entry.get().strip())

        # Criar pasta de saída
        os.makedirs(out_path, exist_ok=True)

        # Processar tags
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        if not tags:
            self.log("❌ Nenhuma tag válida informada!")
            return

        # Conectar ao Telegram
        client = TelegramClient(session, api_id, api_hash)

        try:
            await client.start()
            me = await client.get_me()
            self.log(f"✅ Conectado como: {me.username or me.first_name}")
        except Exception as e:
            self.log(f"❌ Erro ao conectar: {e}")
            return

        csv_path = os.path.join(out_path, "videos_baixados.csv")
        registros = []
        total_baixados = 0
        total_encontrados = 0

        for tag in tags:
            if not self.downloading:
                self.log("⏹ Download cancelado pelo usuário.")
                break

            self.log(f"\n🔍 Procurando vídeos com a tag: {tag}")
            count_tag = 0

            # Resolver entidade
            while self.downloading:
                try:
                    entity = await client.get_input_entity(target)
                    break
                except FloodWaitError as e:
                    self.log(f"⏳ Flood wait ao resolver target ({e.seconds}s)")
                    if e.seconds > max_flood_wait:
                        self.log(
                            f"❌ Flood wait muito longo ({e.seconds}s). Abortando."
                        )
                        await client.disconnect()
                        return
                    self.log(f"→ Aguardando {e.seconds}s...")
                    await asyncio.sleep(e.seconds + 1)

            if not self.downloading:
                break

            # Iterar mensagens
            seen_msg_ids = set()
            while self.downloading:
                try:
                    async for msg in client.iter_messages(
                        entity, search=tag, limit=(limit or None)
                    ):
                        if not self.downloading:
                            break

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

                        # Extrair nome do vídeo
                        lines = [
                            l.strip() for l in msg.message.split("\n") if l.strip()
                        ]
                        video_name = lines[-1] if lines else f"msg{msg.id}"

                        while video_name.startswith("="):
                            video_name = video_name[1:].strip()

                        filename = safe_filename(video_name) + ".mp4"
                        file_path = os.path.join(out_path, filename)

                        if os.path.exists(file_path):
                            self.log(f"⏩ Já existe: {filename}")
                            continue

                        try:
                            self.log(f"⏬ Baixando: {filename}")

                            # Resetar variáveis de progresso
                            self.last_progress_time = time.time()
                            self.last_progress_bytes = 0

                            await client.download_media(
                                msg,
                                file=file_path,
                                progress_callback=self.progress_callback,
                            )

                            self.log(f"✅ Concluído: {filename}")
                            total_baixados += 1
                            count_tag += 1

                            registros.append(
                                {
                                    "tag": tag,
                                    "msg_id": msg.id,
                                    "data": msg.date.strftime("%Y-%m-%d %H:%M:%S")
                                    if msg.date
                                    else "",
                                    "arquivo": filename,
                                    "legenda": msg.message or "",
                                }
                            )

                        except FloodWaitError as e:
                            self.log(f"⏳ Flood wait ({e.seconds}s) → aguardando...")
                            await asyncio.sleep(e.seconds + 1)
                        except Exception as e:
                            self.log(f"❌ Erro ao baixar msg {msg.id}: {e}")

                    # Se terminou sem FloodWait, sair do loop
                    break

                except FloodWaitError as e:
                    self.log(f"⏳ Flood wait durante iteração ({e.seconds}s)")
                    if e.seconds > max_flood_wait:
                        self.log(
                            f"❌ Flood wait muito longo ({e.seconds}s). Abortando."
                        )
                        await client.disconnect()
                        return
                    self.log(f"→ Aguardando {e.seconds}s e reiniciando...")
                    await asyncio.sleep(e.seconds + 1)

            if self.downloading:
                self.log(f"✅ Tag {tag}: {count_tag} vídeos baixados.")

        await client.disconnect()

        # Salvar CSV
        if registros:
            df = pd.DataFrame(registros)
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            self.log(f"\n📄 CSV salvo em: {csv_path}")

        self.log(
            f"\n🚀 Finalizado: {total_baixados} vídeos baixados ({total_encontrados} mensagens verificadas)."
        )
        self.progress_bar.set(1)
        self.progress_label.configure(text="Concluído!")

    def save_config(self):
        """Salva a configuração atual em um arquivo JSON"""
        config = {
            "api_id": self.api_id_entry.get().strip(),
            "api_hash": self.api_hash_entry.get().strip(),
            "target": self.target_entry.get().strip(),
            "tags": self.tags_entry.get().strip(),
            "output_path": self.output_entry.get().strip(),
            "limit": self.limit_entry.get().strip(),
            "session": self.session_entry.get().strip(),
            "max_flood_wait": self.max_flood_entry.get().strip(),
        }

        # Abrir diálogo para salvar arquivo
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Salvar Configuração",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Sucesso", f"Configuração salva em:\n{file_path}")
                self.log(f"✅ Configuração salva: {file_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar configuração:\n{e}")
                self.log(f"❌ Erro ao salvar configuração: {e}")

    def load_config(self):
        """Carrega uma configuração de um arquivo JSON"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Carregar Configuração",
        )

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # Limpar campos
                self.api_id_entry.delete(0, "end")
                self.api_hash_entry.delete(0, "end")
                self.target_entry.delete(0, "end")
                self.tags_entry.delete(0, "end")
                self.output_entry.delete(0, "end")
                self.limit_entry.delete(0, "end")
                self.session_entry.delete(0, "end")
                self.max_flood_entry.delete(0, "end")

                # Preencher com dados carregados
                if "api_id" in config:
                    self.api_id_entry.insert(0, config["api_id"])
                if "api_hash" in config:
                    self.api_hash_entry.insert(0, config["api_hash"])
                if "target" in config:
                    self.target_entry.insert(0, config["target"])
                if "tags" in config:
                    self.tags_entry.insert(0, config["tags"])
                if "output_path" in config:
                    self.output_entry.insert(0, config["output_path"])
                if "limit" in config:
                    self.limit_entry.insert(0, config["limit"])
                if "session" in config:
                    self.session_entry.insert(0, config["session"])
                if "max_flood_wait" in config:
                    self.max_flood_entry.insert(0, config["max_flood_wait"])

                messagebox.showinfo(
                    "Sucesso", f"Configuração carregada de:\n{file_path}"
                )
                self.log(f"✅ Configuração carregada: {file_path}")

            except json.JSONDecodeError:
                messagebox.showerror("Erro", "Arquivo JSON inválido!")
                self.log("❌ Erro: Arquivo JSON inválido")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar configuração:\n{e}")
                self.log(f"❌ Erro ao carregar configuração: {e}")

    def run(self):
        """Inicia a aplicação"""
        self.root.mainloop()


if __name__ == "__main__":
    app = TelegramDownloaderGUI()
    app.run()
