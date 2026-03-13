# MOST Technologies - Desafio Tecnico

## 1. Visão Geral

Este projeto é uma solução de automação ponta a ponta (E2E) para a coleta e estruturação de dados do Portal da Transparência. A arquitetura foi desenhada para processar consultas de beneficiários de programas sociais do governo, superar barreiras de segurança (CAPTCHA) e integrar os resultados automaticamente em ferramentas de produtividade.

## 2. Componentes da Solução

### 2.1. O Bot (Engine de Extração)

O núcleo da solução utiliza automação de navegador para navegar pelo portal. Ele simula o comportamento humano para filtrar buscas e acessar detalhes de pagamentos.

- **Resiliência:** O robô detecta se os componentes da página (como menus e tabelas) estão carregados antes de interagir, evitando erros por lentidão do site.
- **Interação Inteligente:** Utiliza técnicas de simulação de presença de cursor para ativar funções do site que só funcionam quando o usuário interage visualmente com os botões.

### 2.2. A API (Interface de Comunicação)

Toda a lógica do robô é exposta através de uma API moderna.

- **Documentação Automática:** A API gera automaticamente uma interface visual (Swagger) que permite testar os endpoints de consulta sem escrever nenhuma linha de código.
- **Padronização:** Garante que os dados coletados (Nomes, CPFs, Valores) sejam validados e entregues em um formato JSON estruturado e limpo.

### 2.3. Resolução de CAPTCHA (Webhook Telegram)

Para lidar com o sistema de segurança do portal (Amazon WAF), a solução integra um fluxo de interação humana:

1. Ao encontrar um desafio, o sistema captura a imagem e envia para um bot no Telegram.
2. Um operador humano responde ao desafio diretamente pelo chat.
3. **Webhook:** A API possui um canal de escuta (webhook) que recebe essa resposta em tempo real e libera o robô para continuar o trabalho, eliminando interrupções manuais no servidor.

### 2.4. Integração Low-Code (Activepieces)

Os dados extraídos pela API são consumidos por um fluxo de automação no Activepieces:

- **Google Sheets:** Cada consulta gera automaticamente uma nova linha com os dados detalhados do beneficiário.
- **Google Drive:** O sistema gera e armazena um arquivo de evidência (screenshot ou relatório) para auditoria de cada consulta realizada.

## 3. Como Executar

### Pré-requisitos

- Python 3.10 ou superior.
- Navegador Chromium (instalado via Playwright).
- [UV Package manager](https://docs.astral.sh/)

### Instalação

1. Após instalar o uv, execute o comando

```sh
uv sync
```

2. Instale os drivers do navegador:

```sh
uv run playright install chromium
```

- Inicie o servidor localmente (API): `uvicorn main:app --port 8000`
- Ou via docker: `docker compose up --build -d`

## 4. Estrutura de Pastas

- `src/`: Contém os módulos do robô, modelos de dados e serviços de integração.
- `main.py`: Ponto de entrada que sobe a API e os endpoints de Webhook. -`pyproject.toml`: Arquivo de configuração gerenciado pelo UV.
