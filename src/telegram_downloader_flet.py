#!/usr/bin/env python3
import asyncio
import os
import time
import json
from datetime import datetime
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import FloodWaitError
import flet as ft
from typing import Optional, Dict, List
import pandas as pd

# Configuração do Flet
ft.app.target = "web"

def safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in s).strip()

class TelegramDownloaderFlet:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Telegram Video Downloader"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window_width = 1000
        self.page.window_height = 800
        self.page.window_resizable = True
        self.page.padding = 20
        
        # Variáveis de estado
        self.downloading = False
        self.last_progress_time = time.time()
        self.last_progress_bytes = 0
        self.log_content = []
        self.log_visible = True
        
        # Carrega as configurações salvas
        self.config_file = Path('telegram_downloader_config.json')
        self.session_file = Path('telegram_downloader.session')
        self.config = self.load_config()
        
        # Inicializar cliente do Telegram
        self.client = None
        self.phone_code_hash = None
        
        # Inicializar a interface primeiro
        self.setup_ui()
        
        # Preenche os campos com as configurações salvas
        if self.config:
            self.api_id_field.value = self.config.get('api_id', '')
            self.api_hash_field.value = self.config.get('api_hash', '')
            self.target_field.value = self.config.get('target', '')
            self.output_dir_field.value = self.config.get('output_dir', '')
            self.limit_field.value = str(self.config.get('limit', '100'))
            self.tags_field.value = self.config.get('tags', '')
            
        # Atualiza a interface antes de tentar carregar a sessão
        self.page.update()
        
        # Configura o manipulador de redimensionamento de janela
        async def handle_resize(e):
            await self._adjust_ui_elements()
            
        self.page.on_resize = handle_resize
        
        # Tenta carregar a sessão se existir
        print(f"Verificando sessão: {self.session_file} existe? {self.session_file.exists()}")
        print(f"API ID presente: {bool(self.config.get('api_id'))}")
        print(f"API Hash presente: {bool(self.config.get('api_hash'))}")
        
        if self.session_file.exists() and self.config.get('api_id') and self.config.get('api_hash'):
            print("Tentando inicializar cliente com sessão existente...")
            # Usar call_soon para garantir que a UI esteja pronta
            asyncio.get_event_loop().call_soon(
                lambda: asyncio.create_task(self.initialize_client())
            )
    
    async def initialize_client(self):
        """Inicializa o cliente do Telegram com a sessão existente"""
        try:
            print(f"[DEBUG] Inicializando cliente com API ID: {self.config['api_id']}")
            print(f"[DEBUG] Arquivo de sessão: {self.session_file.absolute()}")
            print(f"[DEBUG] Arquivo existe: {self.session_file.exists()}")
            if self.session_file.exists():
                print(f"[DEBUG] Tamanho do arquivo: {self.session_file.stat().st_size} bytes")
                print(f"[DEBUG] Permissões: {oct(self.session_file.stat().st_mode)[-3:]}")
            
            await self.log("🔍 Tentando carregar sessão existente...")
            self.client = TelegramClient(
                str(self.session_file),
                int(self.config['api_id']),
                self.config['api_hash']
            )
            
            print("[DEBUG] Conectando ao Telegram...")
            await self.client.connect()
            print("[DEBUG] Verificando se o usuário está autorizado...")
            is_authorized = await self.client.is_user_authorized()
            print(f"[DEBUG] is_authorized: {is_authorized}")
            
            if is_authorized:
                me = await self.client.get_me()
                print(f"[DEBUG] Usuário autenticado: {me.phone} ({me.first_name} {me.last_name or ''})")
                await self.log(f"✅ Sessão carregada para: {me.phone}")
                self.auth_status.value = f"✅ Autenticado como {me.phone}"
                self.auth_status.color = ft.Colors.GREEN
                self.phone_field.disabled = True
                self.send_code_btn.disabled = True
                self.code_field.disabled = True
                self.verify_code_btn.disabled = True
                self.page.update()
                return True
            else:
                print("[DEBUG] Sessão não autorizada")
                await self.log("ℹ️ Sessão inválida ou expirada, faça login novamente")
                return False
                
        except Exception as e:
            error_msg = f"❌ Erro ao carregar sessão: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            await self.log(error_msg)
            
            # Tenta desconectar o cliente se houver algum problema
            try:
                if hasattr(self, 'client') and self.client and self.client.is_connected():
                    await self.client.disconnect()
            except Exception as de:
                print(f"[DEBUG] Erro ao desconectar: {de}")
                
            return False
    
    def setup_ui(self):
        """Configura a interface do usuário"""
        # Área de autenticação
        self.phone_field = ft.TextField(
            label="Número de telefone (com código do país)",
            hint_text="+5511999999999",
            border_radius=8,
            border_color=ft.Colors.BLUE_GREY_400,
            focused_border_color=ft.Colors.BLUE_400,
        )
        
        self.send_code_btn = ft.ElevatedButton(
            text="Enviar Código",
            on_click=self.send_code_clicked,
            icon="send",
            height=58,  # Altura para alinhar com o campo de telefone
            style=ft.ButtonStyle(
                padding=ft.padding.symmetric(horizontal=16, vertical=8),
            )
        )
        
        self.code_field = ft.TextField(
            label="Código de verificação",
            hint_text="12345",
            expand=True,
            border_radius=8,
            border_color=ft.Colors.BLUE_GREY_400,
            focused_border_color=ft.Colors.BLUE_400,
            disabled=True
        )
        
        self.verify_code_btn = ft.ElevatedButton(
            text="Verificar Código",
            on_click=self.verify_code_clicked,
            icon="verified_user",
            expand=1,
            disabled=True
        )
        
        self.auth_status = ft.Text(
            "❌ Não autenticado",
            color=ft.Colors.RED,
            weight=ft.FontWeight.BOLD
        )
        
        # Configuração dos campos de entrada
        self.api_id_field = ft.TextField(
            label="API ID",
            hint_text="Digite seu API ID",
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
            border_color=ft.Colors.BLUE_GREY_400,
            focused_border_color=ft.Colors.BLUE_400,
        )
        
        self.api_hash_field = ft.TextField(
            label="API Hash",
            hint_text="Digite seu API Hash",
            expand=True,
            password=True,
            can_reveal_password=True,
            border_radius=8,
            border_color=ft.Colors.BLUE_GREY_400,
            focused_border_color=ft.Colors.BLUE_400,
        )
        
        self.target_field = ft.TextField(
            label="Canal/Grupo",
            hint_text="@nome ou https://t.me/nome",
            expand=True,
            border_radius=8,
            border_color=ft.Colors.BLUE_GREY_400,
            focused_border_color=ft.Colors.BLUE_400,
        )
        
        self.tags_field = ft.TextField(
            label="Tags (separadas por vírgula)",
            hint_text="#tag1,#tag2,#tag3",
            expand=True,
            border_radius=8,
            border_color=ft.Colors.BLUE_GREY_400,
            focused_border_color=ft.Colors.BLUE_400,
        )
        
        self.output_dir_field = ft.TextField(
            label="Pasta de saída",
            hint_text="./downloads",
            value="./downloads",
            expand=True,
            read_only=True,
            border_radius=8,
            border_color=ft.Colors.BLUE_GREY_400,
        )
        
        self.browse_btn = ft.ElevatedButton(
            text="Procurar",
            on_click=self.browse_folder,
            style=ft.ButtonStyle(
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            height=50,
        )
        
        self.limit_field = ft.TextField(
            label="Limite de mensagens",
            value="100",
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=8,
            border_color=ft.Colors.BLUE_GREY_400,
            focused_border_color=ft.Colors.BLUE_400,
        )
        
        # Botões principais
        self.download_btn = ft.ElevatedButton(
            text="Iniciar Download",
            on_click=self.start_download,
            style=ft.ButtonStyle(
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.BLUE_700,
                color=ft.Colors.WHITE,
            ),
            height=50,
            expand=True,
        )
        
        self.stop_btn = ft.ElevatedButton(
            text="Parar",
            on_click=self.stop_download,
            style=ft.ButtonStyle(
                padding=20,
                shape=ft.RoundedRectangleBorder(radius=8),
                bgcolor=ft.Colors.RED_700,
                color=ft.Colors.WHITE,
            ),
            height=50,
            expand=True,
            disabled=True,
        )
        
        # Barra de progresso
        self.progress_bar = ft.ProgressBar(
            value=0,
            height=10,
            color=ft.Colors.BLUE_400,
            bgcolor=ft.Colors.GREY_800,
            bar_height=10,
            expand=True,
        )
        
        self.progress_text = ft.Text(
            "Aguardando...",
            size=14,
            color=ft.Colors.GREY_600,
            text_align=ft.TextAlign.CENTER,
        )
        
        self.speed_text = ft.Text(
            "Velocidade: 0 B/s",
            size=12,
            color=ft.Colors.GREY_500,
            text_align=ft.TextAlign.CENTER,
        )
        
        self.current_file_text = ft.Text(
            "Nenhum arquivo em andamento",
            size=14,
            color=ft.Colors.GREY_700,
            weight=ft.FontWeight.W_500,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            text_align=ft.TextAlign.CENTER,
            width=600,
        )
        
        # Área de log
        self.log_view = ft.ListView(
            expand=True,
            spacing=8,
            padding=12,
            auto_scroll=True,
        )
        
        # Botão para mostrar/ocultar log
        self.toggle_log_btn = ft.IconButton(
            icon="KEYBOARD_ARROW_UP",
            on_click=self.toggle_log_visibility,
            tooltip="Ocultar log",
            icon_size=20,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=6),
            )
        )
        
        # Cria o container do log
        self.log_container = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text("Log de Atividades", weight=ft.FontWeight.BOLD, size=14),
                                ft.IconButton(
                                    icon="refresh",
                                    icon_size=16,
                                    on_click=lambda e: self.log_view.controls.clear()
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=ft.padding.symmetric(horizontal=12, vertical=8),
                        bgcolor=ft.Colors.BLUE_700,
                        border_radius=ft.border_radius.only(top_left=6, top_right=6)
                    ),
                    ft.Container(
                        content=self.log_view,
                        expand=True,
                        padding=12,
                        bgcolor=ft.Colors.GREY_900,
                    )
                ],
                spacing=0,
                expand=True,
            ),
            height=200,
            border_radius=6,
            border=ft.border.all(1, ft.Colors.BLUE_700),
            bgcolor=ft.Colors.GREY_900,
            padding=10,
            visible=True,
        )
        
        # Layout principal centralizado
        self.main_container = ft.Container(
            content=ft.Column(
                [
                    # Cabeçalho
                    ft.Container(
                        content=ft.Text(
                            "Telegram Video Downloader",
                            style=ft.TextThemeStyle.HEADLINE_MEDIUM,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        padding=20,
                        alignment=ft.alignment.center,
                    ),
                    
                    # Container centralizador
                    ft.Container(
                        content=ft.Column(
                            [
                                # Área de autenticação
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Row(
                                                [
                                                    ft.Text(
                                                        "Autenticação do Telegram",
                                                        weight=ft.FontWeight.BOLD,
                                                        size=16,
                                                        color=ft.Colors.BLUE_700,
                                                    ),
                                                    self.auth_status
                                                ],
                                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                            ),
                                            ft.Divider(height=1, thickness=1),
                                            ft.Row(
                                                [
                                                    ft.Container(
                                                        content=self.phone_field,
                                                        expand=3,
                                                    ),
                                                    ft.Container(
                                                        content=self.send_code_btn,
                                                        expand=1,
                                                        margin=ft.margin.only(left=10)
                                                    )
                                                ],
                                                spacing=0,
                                                vertical_alignment=ft.CrossAxisAlignment.END,
                                            ),
                                            ft.Row(
                                                [
                                                    self.code_field,
                                                    self.verify_code_btn,
                                                ],
                                                spacing=10,
                                                vertical_alignment=ft.CrossAxisAlignment.END,
                                            ),
                                        ],
                                        spacing=10,
                                    ),
                                    padding=15,
                                    border_radius=10,
                                    border=ft.border.all(1, ft.Colors.BLUE_700),
                                    bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY),
                                    width=800,
                                    margin=ft.margin.symmetric(horizontal=10, vertical=5),
                                )
                            ]
                        ),
                        alignment=ft.alignment.center,
                        expand=True
                    ),
                    
                    # Card de configurações
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Configurações",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.BLUE_700,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                                ft.Row(
                                    [
                                        self.api_id_field,
                                        self.api_hash_field,
                                    ],
                                    spacing=10,
                                ),
                                self.target_field,
                                self.tags_field,
                                ft.Row(
                                    [
                                        self.output_dir_field,
                                        self.browse_btn,
                                    ],
                                    spacing=10,
                                ),
                                ft.Row(
                                    [
                                        self.limit_field,
                                    ]
                                ),
                            ],
                            spacing=15,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                        ),
                        padding=20,
                        border_radius=10,
                        border=ft.border.all(1, ft.Colors.BLUE_700),
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY),
                        width=800,
                        margin=ft.margin.symmetric(horizontal=10, vertical=5),
                ),
                
                    # Botões de controle
                    ft.Container(
                        content=ft.Row(
                            [
                                self.download_btn,
                                self.stop_btn,
                            ],
                            spacing=10,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        padding=10,
                        width=800,
                        margin=ft.margin.symmetric(horizontal=10, vertical=5),
                    ),
                
                    # Área de progresso
                    ft.Container(
                        content=ft.Column(
                            [
                                self.current_file_text,
                                ft.Container(
                                    content=self.progress_bar,
                                    padding=ft.padding.symmetric(vertical=10),
                                ),
                                self.progress_text,
                                self.speed_text,
                            ],
                            spacing=8,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=20,
                        border_radius=10,
                        border=ft.border.all(1, ft.Colors.BLUE_700),
                        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY),
                        width=800,
                        margin=ft.margin.symmetric(horizontal=10, vertical=5),
                    ),
                
                    # Card de log
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Text(
                                                "Log de Atividades",
                                                weight=ft.FontWeight.BOLD,
                                                size=16,
                                                color=ft.Colors.BLUE_700,
                                            ),
                                            ft.IconButton(
                                                icon="remove",
                                                on_click=self.toggle_log_visibility,
                                                icon_size=20,
                                                tooltip="Ocultar/Mostrar Log",
                                            ),
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    ),
                                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                                    bgcolor=ft.Colors.BLUE_700,
                                    border_radius=ft.border_radius.only(top_left=6, top_right=6)
                                ),
                                ft.Container(
                                    content=self.log_view,
                                    expand=True,
                                    padding=12,
                                    bgcolor=ft.Colors.GREY_900,
                                )
                            ],
                            spacing=0,
                            expand=True,
                        ),
                        height=200,
                        border_radius=6,
                        border=ft.border.all(1, ft.Colors.BLUE_700),
                        bgcolor=ft.Colors.GREY_900,
                        padding=10,
                        visible=True,
                        width=800,
                        margin=ft.margin.symmetric(horizontal=10, vertical=5),
                        alignment=ft.alignment.center
                    )
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            expand=True,
            padding=20,
            alignment=ft.alignment.center
        )
        
        # Configuração da página
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.spacing = 20
        
        # Configura o tema da página
        self.page.theme = ft.Theme(
            scrollbar_theme=ft.ScrollbarTheme(
                track_visibility=True,
                track_color=ft.Colors.TRANSPARENT,
                track_border_color=ft.Colors.TRANSPARENT,
                thumb_color={
                    "hover": ft.Colors.BLUE_GREY_500,
                    "": ft.Colors.BLUE_GREY_400,
                },
                thickness=8,
                radius=4,
                main_axis_margin=2,
                cross_axis_margin=2,
            )
        )
        
        # Adiciona o container principal à página
        self.page.add(self.main_container)
        
        # Ajusta os elementos da UI após a renderização inicial
        # Usando call_soon para garantir que a UI esteja pronta
        asyncio.get_event_loop().call_soon(
            lambda: asyncio.create_task(self._adjust_ui_elements())
        )
    
    async def browse_folder(self, e):
        """Abre o diálogo para selecionar a pasta de saída"""
        folder_dialog = ft.FilePicker(on_result=self.folder_selected)
        self.page.overlay.append(folder_dialog)
        self.page.update()
        folder_dialog.get_directory_path(dialog_title="Selecione a pasta de saída")
    
    def load_config(self):
        """Carrega as configurações do arquivo JSON"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.log(f"❌ Erro ao carregar configurações: {e}")
                return {}
        return {}
    
    def save_config(self):
        """Salva as configurações no arquivo JSON"""
        config = {
            'api_id': self.api_id_field.value,
            'api_hash': self.api_hash_field.value,
            'target': self.target_field.value,
            'output_dir': self.output_dir_field.value,
            'limit': self.limit_field.value,
            'tags': self.tags_field.value
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            self.log(f"❌ Erro ao salvar configurações: {e}")
            return False
    
    async def save_config_async(self):
        """Versão assíncrona do save_config para ser usada em callbacks"""
        self.save_config()
    
    async def folder_selected(self, e: ft.FilePickerResultEvent):
        """Callback chamado quando uma pasta é selecionada"""
        if e.path:
            self.output_dir_field.value = e.path
            self.page.update()
            # Salva as configurações quando a pasta é alterada
            await self.save_config_async()
    
    async def _adjust_ui_elements(self):
        """Ajusta elementos da UI após a renderização inicial"""
        try:
            # Ajusta o tamanho dos campos de texto baseado no tamanho da tela
            window_width = self.page.window_width or 1000
            
            # Define tamanhos de fonte responsivos
            if window_width < 600:  # Mobile
                text_size = 12
                padding_size = 10
                # Ajusta o tamanho dos botões para ocupar toda a largura em dispositivos móveis
                for btn in [self.download_btn, self.stop_btn, self.send_code_btn, self.verify_code_btn, self.browse_btn]:
                    if hasattr(btn, 'expand'):
                        btn.expand = True
            elif window_width < 900:  # Tablet
                text_size = 13
                padding_size = 12
                # Ajusta o tamanho dos botões para ocupar metade da largura em tablets
                for btn in [self.download_btn, self.stop_btn]:
                    if hasattr(btn, 'expand'):
                        btn.expand = False
            else:  # Desktop
                text_size = 14
                padding_size = 15
                # Ajusta o tamanho dos botões para largura fixa em desktops
                for btn in [self.download_btn, self.stop_btn]:
                    if hasattr(btn, 'expand'):
                        btn.expand = True
            
            # Atualiza campos de texto
            fields = [
                self.api_id_field, self.api_hash_field, self.target_field,
                self.tags_field, self.output_dir_field, self.limit_field,
                self.phone_field, self.code_field
            ]
            
            for field in fields:
                if field and hasattr(field, 'text_size'):
                    field.text_size = text_size
                    if hasattr(field, 'padding'):
                        field.padding = padding_size
                    field.update()
            
            # Atualiza botões
            buttons = [
                self.send_code_btn, self.verify_code_btn,
                self.download_btn, self.stop_btn, self.browse_btn
            ]
            
            for btn in buttons:
                if btn and hasattr(btn, 'style') and hasattr(btn.style, 'padding'):
                    btn.style.padding = padding_size
                    if hasattr(btn, 'height'):
                        btn.height = 50 if window_width >= 600 else 45
                    btn.update()
            
            # Atualiza a barra de progresso
            if hasattr(self, 'progress_bar'):
                self.progress_bar.height = 10 if window_width >= 600 else 8
                self.progress_bar.update()
            
            # Atualiza o container de log
            if hasattr(self, 'log_container'):
                self.log_container.height = 250 if window_width >= 900 else 200
                self.log_container.update()
            
            # Força a atualização da página
            self.page.update()
            
        except Exception as e:
            print(f"Erro ao ajustar elementos da UI: {e}")
    
    async def _on_page_resize(self, e):
        """Manipulador de redimensionamento da página"""
        try:
            await self._adjust_ui_elements()
        except Exception as e:
            print(f"Erro ao redimensionar: {e}")
    
    async def toggle_log_visibility(self, e):
        """Alterna a visibilidade da área de log"""
        self.log_visible = not self.log_visible
        self.log_container.visible = self.log_visible
        
        # Atualiza o ícone do botão
        if self.log_visible:
            self.toggle_log_btn.icon = "KEYBOARD_ARROW_DOWN"
            self.toggle_log_btn.tooltip = "Ocultar log"
        else:
            self.toggle_log_btn.icon = "KEYBOARD_ARROW_UP"
            self.toggle_log_btn.tooltip = "Mostrar log"
            
        # Força a atualização da UI
        self.page.update()
    
    async def log(self, message: str):
        """Adiciona uma mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_content.append(log_entry)
        
        # Limita o tamanho do log
        while len(self.log_content) > 100:  # Mantém apenas as últimas 100 entradas
            self.log_content.pop(0)
            
        print(log_entry)  # Sempre imprime no console para debug
        
        # Verifica se a UI já foi inicializada
        if not hasattr(self, 'log_view'):
            print("[WARNING] Tentativa de log antes da UI estar pronta:", log_entry)
            return
            
        try:
            # Adiciona a nova mensagem ao log_view
            self.log_view.controls.append(
                ft.Text(
                    log_entry,
                    color=ft.Colors.WHITE,
                    size=12,
                    selectable=True,
                )
            )
            # Rola para a última mensagem
            self.log_view.scroll_to(offset=0, duration=1000)
            self.page.update()
        except Exception as e:
            print(f"[ERRO] Falha ao atualizar log na UI: {e}")
        
    async def send_code_clicked(self, e):
        """Envia o código de verificação para o telefone"""
        if not self.phone_field.value.strip():
            await self.log("❌ Por favor, insira um número de telefone")
            return
            
        if not self.api_id_field.value.strip() or not self.api_hash_field.value.strip():
            await self.log("❌ API ID e Hash são necessários")
            return
            
        self.phone_field.disabled = True
        self.send_code_btn.disabled = True
        self.code_field.disabled = False
        self.verify_code_btn.disabled = False
        self.page.update()
        
        try:
            self.client = TelegramClient(
                str(self.session_file),
                int(self.api_id_field.value),
                self.api_hash_field.value
            )
            await self.client.connect()
            
            # Salva as credenciais no config
            self.config['api_id'] = self.api_id_field.value
            self.config['api_hash'] = self.api_hash_field.value
            self.save_config()
            
            # Envia o código
            response = await self.client.send_code_request(self.phone_field.value)
            self.phone_code_hash = response.phone_code_hash
            await self.log("✅ Código de verificação enviado!")
            
        except Exception as ex:
            await self.log(f"❌ Erro ao enviar código: {ex}")
            self.phone_field.disabled = False
            self.send_code_btn.disabled = False
            self.page.update()
    
    async def verify_code_clicked(self, e):
        """Verifica o código de autenticação"""
        if not self.code_field.value.strip():
            await self.log("❌ Por favor, insira o código de verificação")
            return
            
        try:
            await self.client.sign_in(
                phone=self.phone_field.value,
                code=self.code_field.value,
                phone_code_hash=self.phone_code_hash
            )
            
            await self.log("✅ Autenticado com sucesso!")
            self.auth_status.value = "✅ Autenticado"
            self.auth_status.color = ft.Colors.GREEN
            self.code_field.disabled = True
            self.verify_code_btn.disabled = True
            self.page.update()
            
        except Exception as ex:
            await self.log(f"❌ Erro ao verificar código: {ex}")
    
    async def update_progress(self, current: int, total: int, filename: str = None):
        """Atualiza a barra de progresso e informações do arquivo atual"""
        if total <= 0:
            return
        
        # Calcular progresso
        progress = current / total if total > 0 else 0
        
        # Atualizar nome do arquivo se fornecido
        if filename and hasattr(self, 'current_file_text'):
            self.current_file_text.value = f"Baixando: {filename}"
        
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
        self.progress_bar.value = progress
        
        # Atualizar texto de progresso
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        
        # Calcular ETA
        if speed > 0 and current > 0:
            bytes_remaining = total - current
            eta_seconds = bytes_remaining / speed
            eta_min = int(eta_seconds // 60)
            eta_sec = int(eta_seconds % 60)
            eta_str = f"ETA: {eta_min}m{eta_sec:02d}s"
        else:
            eta_str = "ETA: --"
        
        self.progress_text.value = f"{progress * 100:.1f}% ({current_mb:.1f}/{total_mb:.1f} MB) - {speed_mb:.1f} MB/s - {eta_str}"
        
        return True
    
    async def validate_inputs(self):
        """Valida os campos de entrada"""
        # Validação de campos obrigatórios
        if not self.api_id_field.value.strip():
            await self.log("❌ Erro: API ID é obrigatório!")
            return False
            
        if not self.api_hash_field.value.strip():
            await self.log("❌ Erro: API Hash é obrigatório!")
            return False
            
        if not self.target_field.value.strip():
            await self.log("❌ Erro: Canal/Grupo é obrigatório!")
            return False
            
        if not self.tags_field.value.strip():
            await self.log("❌ Erro: Tags são obrigatórias!")
            return False
            
        output_dir = self.output_dir_field.value.strip()
        if not output_dir:
            await self.log("❌ Erro: Diretório de saída é obrigatório!")
            return False
            
        # Validações numéricas
        try:
            int(self.api_id_field.value.strip())
        except ValueError:
            await self.log("❌ Erro: API ID deve ser um número!")
            return False
            
        try:
            int(self.limit_field.value.strip())
        except ValueError:
            await self.log("❌ Erro: Limite deve ser um número!")
            return False
            
        # Tenta criar o diretório de saída se não existir
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                await self.log(f"❌ Erro ao criar diretório: {e}")
                return False
        
        # Salva as configurações quando os campos são validados
        self.save_config()
        return True
    
    async def start_download(self, e):
        """Inicia o processo de download"""
        if not await self.validate_inputs():
            return
            
        if self.downloading:
            return
            
        self.downloading = True
        self.download_btn.disabled = True
        self.stop_btn.disabled = False
        
        # Limpa o log
        self.log_view.controls.clear()
        self.page.update()
        self.progress_text.value = "Preparando..."
        self.current_file_text.value = "Preparando download..."
        
        # Mostrar a área de log se estiver oculta
        if not self.log_visible:
            await self.toggle_log_visibility(None)
        
        self.page.update()
        
        # Iniciar o download em uma tarefa assíncrona
        asyncio.create_task(self.download_videos())
    
    async def stop_download(self, e):
        """Para o processo de download"""
        self.downloading = False
        await self.log("⏹ Download interrompido pelo usuário")
        self.download_btn.disabled = False
        self.stop_btn.disabled = True
        self.progress_text.value = "Download interrompido"
        self.page.update()
    
    async def download_videos(self):
        """Função principal de download"""
        try:
            # Verificar autenticação
            if not self.client or not await self.client.is_user_authorized():
                error_msg = "❌ Por favor, faça login primeiro"
                await self.log(error_msg)
                return False
                
            # Obter parâmetros
            target = self.target_field.value.strip()
            tags_str = self.tags_field.value.strip()
            out_path = self.output_dir_field.value.strip()
            
            try:
                limit = int(self.limit_field.value.strip())
                if limit <= 0:
                    error_msg = "❌ O limite deve ser maior que zero"
                    await self.log(error_msg)
                    return False
            except ValueError:
                error_msg = "❌ O limite deve ser um número válido"
                await self.log(error_msg)
                return False
            
            # Processar tags
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            if not tags:
                error_msg = "❌ Nenhuma tag válida informada!"
                await self.log(error_msg)
                return False
            
            # Usar o cliente já autenticado
            client = self.client
            
            try:
                # Verifica se o cliente está conectado (sem await)
                if not client.is_connected():
                    await client.connect()
                
                if not await client.is_user_authorized():
                    error_msg = "❌ Sessão inválida, faça login novamente"
                    await self.log(error_msg)
                    return False
                
                # Criar diretório de saída se não existir
                if not os.path.isdir(out_path):
                    try:
                        os.makedirs(out_path, exist_ok=True)
                    except Exception as e:
                        error_msg = f"❌ Erro ao criar diretório de saída: {e}"
                        await self.log(error_msg)
                        return False
                
                if not os.path.isdir(out_path):
                    error_msg = f"❌ O diretório de saída não existe: {out_path}"
                    await self.log(error_msg)
                    return False
                
                await self.log(f"🔍 Procurando mensagens em {target} com as tags: {', '.join(tags)}")
                
                # Obter a entidade do alvo (canal/grupo)
                try:
                    entity = await client.get_entity(target)
                    await self.log(f"✅ Conectado a: {entity.title}")
                except Exception as e:
                    error_msg = f"❌ Erro ao acessar o canal/grupo: {e}"
                    await self.log(error_msg)
                    return False
                
                # Buscar mensagens
                messages = []
                try:
                    await self.log("🔍 Buscando mensagens...")
                    # Buscar todas as mensagens primeiro
                    all_messages = []
                    async for message in client.iter_messages(entity, limit=limit):
                        if not self.downloading:
                            await self.log("⏹ Busca interrompida pelo usuário")
                            break
                            
                        if message.text and any(tag.lower() in message.text.lower() for tag in tags):
                            all_messages.append(message)
                            await self.log(f"📝 Mensagem encontrada: {message.text[:50]}...")
                            
                            # Atualizar a interface periodicamente para não travar
                            if len(all_messages) % 5 == 0:
                                self.page.update()
                    
                    # Inverter a ordem para baixar da mais antiga para a mais recente
                    messages = all_messages[::-1]
                    
                    if not messages:
                        info_msg = "ℹ️ Nenhuma mensagem encontrada com as tags fornecidas"
                        await self.log(info_msg)
                        return True
                        
                    await self.log(f"✅ Encontradas {len(messages)} mensagens com as tags informadas")
                    
                except Exception as e:
                    error_msg = f"❌ Erro ao buscar mensagens: {e}"
                    await self.log(error_msg)
                    return False
                
                # Baixar mídias
                downloaded_count = 0
                for i, message in enumerate(messages, 1):
                    if not self.downloading:
                        await self.log("⏹ Download interrompido pelo usuário")
                        break
                        
                    if message.media:
                        try:
                            # Extrair nome do vídeo da última linha da mensagem
                            lines = [l.strip() for l in message.text.split('\n') if l.strip()] if message.text else []
                            video_name = lines[-1] if lines else f"msg{message.id}"
                            
                            # Remover prefixos como "===" , "==", "=" do início
                            while video_name.startswith('='):
                                video_name = video_name[1:].strip()
                            
                            # Garantir que o diretório de saída existe
                            os.makedirs(out_path, exist_ok=True)
                            
                            # Nome do arquivo baseado na última linha da mensagem
                            date_str = message.date.strftime("%Y%m%d_%H%M%S") if message.date else "nodate"
                            file_name = safe_filename(video_name) + ".mp4"
                            
                            # Se não tiver um nome válido, usar o ID da mensagem
                            if not file_name or file_name == ".mp4":
                                file_name = f"msg{message.id}.mp4"
                            
                            # Caminho completo do arquivo
                            full_path = os.path.join(out_path, file_name)
                            
                            # Verifica se o arquivo já existe
                            if os.path.exists(full_path):
                                await self.log(f"⏩ Já existe: {file_name}")
                                continue
                                
                            # Verifica se há arquivos com o mesmo padrão (com sufixo numérico)
                            base_name, ext = os.path.splitext(file_name)
                            matching_files = [f for f in os.listdir(out_path) 
                                           if f.startswith(base_name) and f.endswith(ext)]
                            
                            if matching_files:
                                await self.log(f"⏩ Já existe versão de: {file_name}")
                                continue
                            
                            # Atualizar status com o nome do arquivo
                            self.current_file_text.value = f"Baixando: {os.path.basename(full_path)}"
                            self.page.update()
                            
                            # Baixar o arquivo diretamente para o caminho especificado
                            file_path = await client.download_media(
                                message,
                                file=full_path,
                                progress_callback=lambda c, t: asyncio.create_task(
                                    self.update_progress(c, t, os.path.basename(full_path))
                                )
                            )
                            
                            if os.path.exists(full_path):
                                downloaded_count += 1
                                success_msg = f"✅ Arquivo salvo: {os.path.basename(full_path)}"
                                await self.log(success_msg)
                                
                                # Atualizar a interface periodicamente
                                if downloaded_count % 3 == 0:
                                    self.page.update()
                            
                        except Exception as e:
                            error_msg = f"❌ Erro ao baixar mídia: {e}"
                            await self.log(error_msg)
                            # Não interrompe o download dos demais arquivos
                
                # Resultado final
                if self.downloading:
                    success_msg = f"✅ Download concluído! {downloaded_count} arquivo(s) baixado(s)"
                    await self.log(success_msg)
                    self.progress_text.value = "Download concluído"
                    return True
                else:
                    await self.log("⏹ Download interrompido")
                    return False
                    
            except Exception as e:
                error_msg = f"❌ Erro durante o download: {e}"
                await self.log(error_msg)
                import traceback
                await self.log(traceback.format_exc())
                return False
                
        except Exception as e:
            error_msg = f"❌ Erro inesperado: {e}"
            await self.log(error_msg)
            import traceback
            await self.log(traceback.format_exc())
            return False
            
        finally:
            self.downloading = False
            self.download_btn.disabled = False
            self.stop_btn.disabled = True
            
            # Fechar a conexão se estiver aberta
            try:
                if hasattr(self, 'client') and self.client and self.client.is_connected():
                    await self.client.disconnect()
            except Exception as e:
                await self.log(f"⚠️ Aviso ao desconectar: {e}")
            
            self.page.update()

async def main(page: ft.Page):
    """Função principal da aplicação"""
    # Criar e configurar a aplicação
    app = TelegramDownloaderFlet(page)
    
    # Configurar tema
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.BLUE
    )
    
    # Configurar atualizações automáticas
    page.update()

# Iniciar a aplicação
if __name__ == "__main__":
    ft.app(target=main)
