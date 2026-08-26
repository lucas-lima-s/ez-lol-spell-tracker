# EzSpellTrackerV2 — Roadmap

> Criado em 2026-06-10, com base na pesquisa de ferramentas existentes (Porofessor, Mobalytics,
> tracker.gg, OP.GG, 10+ projetos open-source), nas APIs oficiais da Riot e na autópsia dos
> projetos `League-spell-tracker` e `EzSpellTracker`.

## Visão

Tracker de summoner spells inimigas para League of Legends: app de bandeja do sistema que detecta
a partida automaticamente, popula os 5 inimigos (campeão + spells) e exibe um overlay in-game
arrastável onde um clique inicia o timer de cooldown da spell. 100% local, 100% dentro da política
de terceiros da Riot.

## Decisões de arquitetura

### Stack

- **Python 3.13+ (3.14 na máquina atual) + PySide6** (overlay, tray, settings UI), `requests`
  (APIs), `pytest` (testes). Atenção: builds free-threaded (3.14t) não servem — PySide6 não tem
  wheels para eles; o bootstrap dos `.bat` rejeita automaticamente.
- **Dev:** ambiente autocontido estilo EzSpellTracker v1 — `build_environment.bat` vendoriza as
  dependências em `lib/` (`pip install --target=lib`), `run.bat` executa com `PYTHONPATH=lib`.
  Correção obrigatória do bug do v1: o parsing de `configs.json` nos `.bat` deve ser feito por
  Python (bootstrap), nunca por `findstr`.
- **Release:** PyInstaller **onedir** (nunca onefile) com `--add-data` para `assets/` — pasta
  autocontida, sem instalação de runtime pelo usuário.

### Fontes de dados (todas oficiais)

| Dado | Fonte |
|---|---|
| Partida em andamento, roster, campeões, spells equipadas, itens | Live Client Data API — `https://127.0.0.1:2999/liveclientdata/` (`/allgamedata`, `/playerlist`, `/gamestats`) |
| Cooldowns base das spells por patch | Data Dragon `summoner.json` (com tabela de fallback validada manualmente) |
| Sprites (campeões, spells) e versão do patch | Data Dragon `versions.json` + `/cdn/{ver}/img/...`; CommunityDragon `latest` como fallback em dia de patch |

Regras derivadas da autópsia do projeto base:

- **Zero dependência de rede externa no caminho crítico** — o jogo só fala com `127.0.0.1:2999`;
  Data Dragon é usado apenas para atualizar cache local de assets/dados. Sem Firebase, sem conta.
- **Independência de locale do cliente** (o cliente do usuário é pt-BR): identificar spells pelo
  `rawDisplayName` (ex.: `..._SummonerFlash_...`), nunca pelo `displayName` localizado.
- Cooldown ancorado no `gameTime` da API, não no relógio de parede (sobrevive a pause/reconexão).

### Anti-detecção (estratégia: nada para detectar)

FAQ oficial do Vanguard: *"Overlays and internal tools using the API, game client, and in-game
APIs should continue to function"*. O que o Vanguard mata é injeção e leitura de memória.

1. Janela de overlay **externa** (frameless, transparente, topmost) — zero injeção de DLL, zero
   hook em DirectX, zero leitura de memória/processo do jogo.
2. Apenas APIs oficiais locais (endpoint 2999, endossado pela Riot para este fim).
3. Título/classe de janela neutros e genéricos; `Qt.Tool` (fora da taskbar e do Alt+Tab).
4. Toggle nas configurações: **ocultar overlay de gravações/replays/streams**
   (`SetWindowDisplayAffinity WDA_EXCLUDEFROMCAPTURE`, Win10 2004+). Off por padrão.
5. TLS com `riotgames.pem` embarcado (pin do cert self-signed da Riot) em vez de `verify=False`.
6. Captura de tela (quando existir, v2.1) apenas por APIs públicas de captura (WGC) — leitura
   passiva, idêntica ao OBS.

### Restrições conhecidas (não são bugs)

- **Uso de spell inimiga não é detectável automaticamente** por nenhuma via legítima: a API não
  expõe cooldown/cast inimigo e o scoreboard não renderiza esse estado (não há o que a visão
  computacional ler). Início de timer é manual por design — padrão de toda a indústria.
- **LoL deve rodar em Borderless** (janela sem bordas) para o overlay externo renderizar por cima
  com garantia. Fullscreen exclusivo funciona às vezes no Win11 (FSO), sem garantia — documentar
  no primeiro uso.
- Runas inimigas (Inspiração Cósmica) não são expostas pela API → ajuste manual (v2.0).

## Não-escopo (decisões registradas)

| Item | Motivo |
|---|---|
| Tracking de ultimates | **Banido pela Riot em 2025-03-13** (manual ou automático, tratado como cheating, enforcement via Vanguard). Decisão 2026-06-10: removido do roadmap. |
| Sync de timers entre membros do time | Decisão 2026-06-10: fora do escopo. Foi a dependência (Firebase) que quebrou o projeto base. |
| Leitura de memória / injeção / hooks | Violação de política + detecção Vanguard. Nunca. |
| Auto-detecção de cast por CV | Tecnicamente impossível (nada renderizado na tela) e zona cinzenta de política. |
| Anúncios no overlay | Banido pela Riot em 2025-05-29. |

## Estrutura de pastas (alvo)

```
EzSpellTrackerV2/
├── run.bat                  # dev: PYTHONPATH=lib + python src/main.py
├── build_environment.bat    # dev: vendoriza deps em lib/
├── build_release.bat        # PyInstaller onedir autocontido
├── configs.json             # bootstrap (pythonPath) — só para os .bat de dev
├── requirements.txt         # deps pinadas
├── ROADMAP.md
├── assets/                  # snapshot embarcado (funciona offline no 1º uso)
│   ├── champions/           # sprites quadrados (reaproveitar dos projetos v1)
│   ├── spells/              # ícones de summoner spells
│   └── data/                # summoner.json, champions.json, version.txt (cache por versão)
├── lib/                     # deps vendorizadas (gitignored)
├── src/
│   ├── main.py              # entrypoint: tray + event loop
│   ├── app/                 # TrayIcon, SettingsWindow
│   ├── core/                # config (settings.json do usuário), logging, models, cooldown math
│   ├── riot/                # live_client.py, ddragon.py, asset_updater.py
│   ├── overlay/             # OverlayWindow, EnemyRow, timers
│   └── capture/             # v2.1 — captura WGC (ancoragem/calibração)
└── tests/
```

## Fases

### v0.1 — Fundação

**Escopo:** esqueleto do projeto na estrutura acima; `build_environment.bat`/`run.bat` corrigidos
(bootstrap de config via Python); config do usuário (`settings.json`) com persistência; logging
rotativo; app de tray funcional (QSystemTrayIcon): duplo clique abre janela de configurações
(ainda vazia), menu de contexto com Configurações/Mostrar overlay/Sair.

**Critérios de conclusão:** `build_environment.bat` em máquina limpa instala tudo em `lib/`;
`run.bat` sobe o app na bandeja; duplo clique abre a janela; sair encerra limpo.
**Testes:** `pytest tests/test_config.py tests/test_logging.py`

### v0.2 — Integração Riot

**Escopo:** cliente da Live Client Data API (poll de `/gamestats` para detectar partida,
`/allgamedata` para roster) com cert da Riot pinado; identificação do time inimigo via
`activePlayer` + `riotId`; extração de campeão + spells por `rawDisplayName` (locale-independente,
validar com cliente pt-BR); modelos de domínio (Enemy, SpellSlot, cooldown math
`base / (1 + haste/100)`); snapshot Data Dragon baixado por `scripts/fetch_assets.py` (sprites
com naming canônico por id — substitui a migração dos sprites antigos); tabela de cooldowns base
carregada do `summoner.json` embarcado.

**Critérios de conclusão:** com uma partida ao vivo (ou Practice Tool), o log mostra os 5
inimigos com campeão e spells corretos em cliente pt-BR; testes de parsing passam com fixtures
JSON reais gravadas.
**Testes:** `pytest tests/test_live_client.py tests/test_models.py tests/test_cooldowns.py`

### v1.0 — Overlay tracker (MVP utilizável)

**Escopo:** overlay no layout da imagem de referência (coluna vertical: retrato do campeão + 2
ícones de spell, timer MM:SS sobreposto ao ícone em cooldown); clique esquerdo inicia timer,
clique direito reseta; arrastável com toggle de lock; aparece automaticamente ao detectar partida
e some ao terminar; mostra apenas com a janela do LoL ativa; heartbeat topmost; janela de
configurações completa — **toda configuração via UI**: posição (reset), escala, opacidade,
lock, ocultar de gravações (WDA), iniciar com Windows; `build_release.bat` gerando pasta
autocontida testada em máquina limpa.

**Critérios de conclusão:** partida real jogada do início ao fim usando o tracker em 2560x1440;
timers corretos; overlay não rouba foco do jogo ao clicar (`WS_EX_NOACTIVATE`); release onedir
roda sem Python instalado.
**Testes:** `pytest tests/` + checklist manual in-game (documentado em `tests/MANUAL.md`)

### v1.1 — Auto-update de sprites e dados por patch

**Escopo:** `asset_updater.py` — no startup (e a cada N horas), compara `versions.json[0]` com o
cache local; se houver patch novo, baixa `champion.json`, `summoner.json` e sprites faltantes
para cache por versão; fallback CommunityDragon `latest` para campeão recém-lançado ainda ausente
no Data Dragon; tudo assíncrono (nunca bloqueia o overlay); indicador de versão do patch na
janela de configurações.

**Critérios de conclusão:** apagar um sprite do cache e subir o app → sprite rebaixado
automaticamente; simular versão antiga no cache → atualização completa sem intervenção.
**Testes:** `pytest tests/test_asset_updater.py` (com HTTP mockado)

### v2.0 — Cooldowns autoajustáveis

**Escopo:** poll periódico de `/playerlist` para os itens dos inimigos → detecção automática de
Botas Ionianas (haste de summoner spell aplicado ao cálculo); toggle manual de Inspiração Cósmica
por inimigo (runas não são expostas pela API); botões de ajuste fino no overlay (-10s/-30s para
marcação atrasada) e offset configurável "assumir cast há N segundos"; casos especiais: Teleport
→ Unleashed Teleport por tempo de jogo, Smite por cargas.

**Critérios de conclusão:** inimigo compra Botas Ionianas → timer seguinte usa cooldown reduzido
sem input do usuário; valores de haste validados contra o patch corrente (não confiar cegamente
em valores antigos).
**Testes:** `pytest tests/test_cooldowns.py tests/test_item_detection.py`

### v2.1 — Módulo de captura de tela (suporte/QoL)

**Escopo:** captura passiva da janela do LoL via Windows.Graphics.Capture em baixa frequência
(2–5 fps, região pequena) para: ancoragem/calibração automática da posição do overlay por
resolução/HUD scale, detecção de estado de tela (TAB aberto, loading) para auto-ocultar/realocar.
Explicitamente **não** usado para detectar casts (impossível). Sprites de referência escalados
deterministicamente (`escala = altura_captura / 1080`).

**Critérios de conclusão:** trocar resolução (1080p ↔ 1440p) reposiciona/escala o overlay sem
ajuste manual; consumo de CPU da captura < 2%.
**Testes:** `pytest tests/test_capture.py` (com frames de fixture)

## Validações pendentes (registradas em 2026-06-11 a pedido do usuário)

Os testes automatizados das fases passam, mas as validações AO VIVO continuam necessárias e
ainda não foram executadas — checklist completo em `tests/MANUAL.md`:

- [ ] **v0.2** — validação ao vivo do roster (Practice Tool, cliente pt-BR, 5 bots; conferir
      `riotId` no `activePlayer` real).
- [ ] **v1.0** — checklist manual completo: partida real 2560×1440 Borderless, foco
      NOACTIVATE (teste do Notepad + in-game), pause congelando timers, WDA com OBS,
      iniciar com Windows, Fullscreen exclusivo (documentar), release em máquina sem Python.
- [ ] **v1.0.1** — features de UI: config por resolução, cadeado no overlay, hotkey
      mostrar/ocultar (default F8), opacidade — seção própria no `tests/MANUAL.md`.
- [ ] **v1.1** — auto-update de assets em background (apagar sprite/regredir version.txt e
      validar re-download; label de versão nas configurações).
- [ ] **v2.0** — cooldowns autoajustáveis: botas detectadas via API (ponto azul), Inspiração
      Cósmica manual (clique direito no retrato, ponto amarelo), roda do mouse ±5 s,
      compensação de clique, Smite 90 s, Unleashed TP pós-10:00. Constantes verificadas no
      wiki em 2026-06-11 — reconferir por patch.

**v2.1 (captura de tela) adiada deliberadamente**: calibração de ancoragem exige sessões ao
vivo com o jogo aberto em várias resoluções — será implementada com o usuário presente, após
as validações acima.

## Backlog (sem compromisso)

- Hotkeys globais configuráveis para marcar spells sem usar o mouse.
- Botão "copiar timer para o chat" (formato clássico `flash mid 14:32` no clipboard — nunca
  enviar teclas ao jogo automaticamente).
- Timers de objetivos/jungle próprios (permitidos pela política).
- Registro do app no Riot Developer Portal (trackers open-source pequenos já foram aprovados).

## Questões em aberto

- Valor atual de haste das Botas Ionianas no patch corrente (fontes divergem: 10 vs 12) —
  verificar no patch vigente antes da v2.0.
- Presença/formato de `riotId`/`rawDisplayName` no `/playerlist` com cliente pt-BR — validar ao
  vivo na v0.2.
- Comportamento do overlay com LoL em Fullscreen exclusivo na máquina do usuário (Win11 FSO) —
  testar na v1.0; se funcionar, documentar como suportado.
- Riot está testando spell tracker nativo no PBE (Season 2026) — acompanhar; se lançar, o app
  segue útil como referência/estudo.
- Política da Riot sobre summoner spell tracking está "em discussão interna" (declaração de
  maio/2025) — manter o módulo de timers isolado para desativação rápida se a política mudar.
