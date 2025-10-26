# Telegram Downloader Tools

Este projeto permite baixar vídeos do Telegram utilizando múltiplas hashtags. É uma ferramenta útil para coletar conteúdo de canais ou grupos específicos.

## Pré-requisitos

- Python 3.6 ou superior
- Telethon
- Pandas

## Obter API ID e API Hash

1. Acesse https://my.telegram.org e faça login com seu número de telefone.
2. Depois do login, clique em "API development tools".
3. Preencha o formulário para criar uma nova aplicação (App title, Short name, etc.). Ao finalizar, você verá o seu "api_id" e "api_hash".

## Instalação

1. Clone o repositório:
   ```
   git clone https://github.com/vinicius-dsr/Telegram-Downloader-Tools.git
   cd telegram-downloader-tools
   ```

2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

## Uso

Para usar a ferramenta, execute o seguinte comando:

```
python src/download_telegram_video_tags.py --api-id SEU_API_ID --api-hash SEU_API_HASH --target "https://t.me/nomeCanal" --tags "#tag1,#tag2" --out "./downloads"
```

## FloodWait (limitação de requisições)

Ao usar a API do Telegram via Telethon, é possível receber uma exceção `FloodWaitError` quando a conta faz muitas requisições em pouco tempo. O Telegram exige então que você aguarde um certo número de segundos antes de tentar novamente — esse tempo pode variar de alguns segundos a vários minutos.

O script trata FloodWait de três formas principais:

- Retry controlado ao resolver a entidade do `--target` (reduce chamadas repetidas que causam `CheckChatInviteRequest`).
- Retry quando a iteração por mensagens encontra `FloodWaitError`: o script espera o tempo solicitado e reinicia a iteração.
- Você pode controlar o comportamento automático com o argumento `--max-flood-wait` (valor em segundos).

Com `--max-flood-wait`:
- Se o FloodWait requerido (`e.seconds`) for menor ou igual ao valor informado, o script aguardará automaticamente `e.seconds + 1` e continuará.
- Se o FloodWait for maior que `--max-flood-wait`, o script aborta imediatamente e mostra uma instrução clara (para você aguardar manualmente ou reapertar o comando com `--max-flood-wait` maior).

Valores recomendados:
- `0`: não aceitar waits automáticos (o script aborta ao primeiro FloodWait). Útil para não deixar o processo bloqueado.
- `30` ou `60`: aceitar waits curtos automaticamente.
- `300` (padrão atual do script): aceita waits de até 5 minutos automaticamente.

Exemplos:

```sh
# aborta imediatamente em qualquer FloodWait
python3 src/download_telegram_video_tags.py --api-id 123 --api-hash 'SEU_HASH' --target '@canal' --tags '#tag' --max-flood-wait 0

# aceita esperar até 60 segundos automaticamente
python3 src/download_telegram_video_tags.py --api-id 123 --api-hash 'SEU_HASH' --target '@canal' --tags '#tag' --max-flood-wait 60

# aceita esperar até 1974 segundos (ex.: aceitar um FloodWait específico que apareceu antes)
python3 src/download_telegram_video_tags.py --api-id 123 --api-hash 'SEU_HASH' --target '@canal' --tags '#tag' --max-flood-wait 1974
```

Boas práticas para reduzir FloodWaits:
- Reduza o número de requisições por execução (`--limit` menor, menos tags por vez).
- Espalhe as execuções no tempo (rodar em batches com sleep entre eles).
- Use outra conta/sessão para distribuir carga se necessário.

Se o script abortar com uma mensagem de FloodWait longa, você pode optar por:
- aguardar o tempo indicado manualmente e rodar novamente;
- reexecutar com `--max-flood-wait` maior (aceitar que o processo fique aguardando);
- reduzir a taxa de requisições e tentar novamente mais tarde.

## Canais do Telegram

- https://t.me/+hy2KQlxP78JiYmIx
- https://t.me/+PxqctwKBOjMxMjli


## Contribuição

Sinta-se à vontade para contribuir com melhorias ou correções. Faça um fork do repositório e envie um pull request.
