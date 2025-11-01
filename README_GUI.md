# 📥 Telegram Video Downloader - Interface Gráfica

Interface gráfica moderna para baixar vídeos do Telegram por hashtags usando **tkinter** e **customtkinter**.

## 🎨 Características

- ✨ Interface gráfica moderna com tema escuro
- 📊 Barra de progresso visual em tempo real
- 📝 Área de log detalhada
- ⚡ Download assíncrono com velocidade e ETA
- 🛑 Botão para parar downloads em andamento
- 💾 Exportação automática para CSV
- 🔒 Campo de API Hash mascarado

## 📋 Pré-requisitos

1. Python 3.7 ou superior
2. Conta no Telegram
3. API ID e API Hash (obtenha em: https://my.telegram.org)

## 🚀 Instalação

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd Telegram-Downloader-Tools
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## 💻 Como Usar

### Iniciar a Interface Gráfica

```bash
python src/download_telegram_video_tags_gui.py
```

### Preenchendo os Campos

1. **API ID**: Seu ID da API do Telegram (número)
2. **API Hash**: Seu Hash da API do Telegram
3. **Canal/Grupo**: 
   - Formato: `@nomecanal` ou `https://t.me/nomecanal`
4. **Tags**: 
   - Hashtags separadas por vírgula
   - Exemplo: `#tag1,#tag2,#tag3`
5. **Pasta de saída**: 
   - Local onde os vídeos serão salvos
   - Padrão: `./downloads`
   - Use o botão "Procurar" para selecionar uma pasta
6. **Limite por tag**: 
   - Número de vídeos a baixar por tag
   - 0 = sem limite
7. **Nome da sessão**: 
   - Nome do arquivo de sessão do Telethon
   - Padrão: `session`
8. **Max Flood Wait (s)**: 
   - Tempo máximo de espera em caso de flood wait
   - Padrão: 300 segundos (5 minutos)

### Iniciando o Download

1. Preencha todos os campos obrigatórios
2. Clique no botão **"🚀 Iniciar Download"**
3. Na primeira execução, você precisará autenticar com o Telegram (código enviado para seu app)
4. Acompanhe o progresso na barra de progresso e na área de log

### Durante o Download

- **Barra de progresso**: Mostra o progresso do arquivo atual
- **Área de log**: Exibe todas as ações e mensagens
- **Botão Parar**: Cancela o download em andamento

## 📁 Arquivos Gerados

Após o download, você encontrará:

1. **Vídeos**: Salvos na pasta especificada com nome seguro
2. **CSV**: `videos_baixados.csv` com informações detalhadas:
   - Tag usada
   - ID da mensagem
   - Data e hora
   - Nome do arquivo
   - Legenda completa

## 🎯 Recursos da Interface

### Validação de Campos
- Verifica se todos os campos obrigatórios foram preenchidos
- Valida se API ID, Limite e Max Flood Wait são números

### Progresso em Tempo Real
- Porcentagem de download
- Tamanho baixado / Total
- Velocidade de download (MB/s)
- Tempo estimado restante (ETA)

### Log Detalhado
- Status de conexão
- Tags sendo processadas
- Vídeos encontrados e baixados
- Erros e avisos
- Situações de flood wait

## 🛠️ Versão CLI

Se preferir usar a versão em linha de comando, consulte o arquivo original:
```bash
python src/download_telegram_video_tags.py --help
```

## ⚠️ Observações Importantes

1. **Primeira Execução**: Você precisará fazer login no Telegram
2. **Flood Wait**: O Telegram pode limitar requisições. A aplicação aguarda automaticamente
3. **Arquivos Existentes**: Vídeos já baixados são pulados automaticamente
4. **Sessão**: O arquivo de sessão mantém você logado entre execuções

## 🎨 Personalização

A interface usa **customtkinter** com tema escuro por padrão. Para mudar:

No arquivo `src/download_telegram_video_tags_gui.py`, linha 14:
```python
ctk.set_appearance_mode("dark")  # Altere para "light" ou "system"
ctk.set_default_color_theme("blue")  # Altere para "green" ou "dark-blue"
```

## 📝 Exemplo de Uso

1. API ID: `12345678`
2. API Hash: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`
3. Canal/Grupo: `@meucanal`
4. Tags: `#video,#download,#conteudo`
5. Pasta de saída: `C:/Downloads/Telegram`
6. Clique em "Iniciar Download"

## 🐛 Solução de Problemas

### Erro ao importar customtkinter
```bash
pip install customtkinter --upgrade
```

### Erro de conexão do Telegram
- Verifique suas credenciais API ID e API Hash
- Certifique-se de estar conectado à internet

### Flood Wait muito longo
- Aumente o valor de "Max Flood Wait"
- Ou aguarde manualmente e tente novamente mais tarde

## 📄 Licença

Este projeto está sob a mesma licença do repositório original.

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.
