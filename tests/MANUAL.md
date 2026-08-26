# Checklist de validação manual

> Pendências registradas em 2026-06-11 (pedido do usuário: validações ao vivo adiadas).
> Marcar cada item ao validar. Itens v0.2 e v1.0 podem ser validados juntos.

## v0.2 — Validação ao vivo da integração Riot (PENDENTE)

- [ ] Abrir o app (`run.bat`), criar Practice Tool com 5 bots inimigos → `logs\app.log` mostra
      `Game detected` e 1 linha por inimigo com campeão (id canônico) + spells corretos em
      cliente pt-BR.
- [ ] Conferir no log se o `activePlayer` real expôs `riotId` (questão aberta do sample antigo).
- [ ] Practice Tool sem bots → warning "Game started with no enemies on roster".
- [ ] Sair da partida → `Game ended` em ~6 s.

## v1.0 — Preview e posicionamento

- [ ] Bandeja → "Mostrar overlay" exibe 5 linhas placeholder (Annie/Ahri/Garen/Lux/Teemo) com
      sprites reais.
- [ ] Arrastar o overlay reposiciona; posição persiste após fechar/reabrir o app.
- [ ] Configurações → Bloquear posição impede arrasto; borda some quando travado.
- [ ] Sliders de escala/opacidade aplicam ao vivo; Redefinir posição volta ao padrão.
- [ ] Clique esquerdo num ícone inicia timer M:SS com ícone acinzentado; direito reseta.

## v1.0 — Foco (critério NOACTIVATE)

- [ ] Teste do Notepad: digitar continuamente no Notepad e clicar em vários ícones do overlay
      (preview) — o cursor de texto permanece no Notepad, a digitação não é interrompida e a
      barra de título do Notepad continua com cor de janela ativa.
- [ ] In-game: segurar comando de movimento / digitar no chat e clicar no overlay — o
      personagem continua respondendo, o chat mantém o foco, o jogo nunca minimiza.

## v1.0 — Partida real (2560×1440, Borderless)

- [ ] Overlay aparece sozinho após o loading e some no fim da partida.
- [ ] 5 inimigos corretos (cliente pt-BR), timers corretos comparados a um cronômetro.
- [ ] Pause (Practice Tool) congela os timers; despause retoma.
- [ ] Alt-tab esconde o overlay; voltar ao jogo reexibe; overlay permanece por cima do jogo
      durante toda a partida (heartbeat).
- [ ] Testar também em Fullscreen exclusivo e anotar o resultado aqui (questão aberta do
      roadmap): ___________

## v1.0.1 — Features de UI (pedido de 2026-06-11)

### Config por resolução
- [ ] Posicionar/escalar o overlay em 2560×1440; mudar a resolução do Windows (ou do jogo em
      Borderless) para 1920×1080 → overlay recarrega posição/escala do perfil da nova
      resolução (default na primeira vez); voltar para 2560×1440 → posição/escala originais
      restauradas sem ajuste manual.
- [ ] Janela de configurações mostra "Perfil de resolução atual: <WxH>" correto.
- [ ] `config/settings.json` guarda perfis separados em `overlay.profiles`.

### Ícone de cadeado no overlay
- [ ] Cadeado aparece no topo direito do overlay (aberto = destravado, com borda; fechado =
      travado, sem borda).
- [ ] Clique no cadeado IN-GAME trava/destrava sem roubar o foco do jogo.
- [ ] Travado: arrasto não move o overlay; cliques nas spells continuam funcionando.
- [ ] Checkbox "Bloquear posição" nas configurações reflete o estado ao clicar no cadeado
      (e vice-versa).

### Hotkey mostrar/ocultar
- [ ] Com o default F8: pressionar IN-GAME (jogo com foco) esconde o overlay; pressionar de
      novo mostra. Funciona também no preview.
- [ ] Trocar o atalho nas configurações (ex.: Ctrl+F9) → novo atalho funciona imediatamente e
      persiste após reiniciar o app.
- [ ] Atalho em conflito (registrado por outro app) → aviso aparece e o atalho anterior
      continua valendo.
- [ ] Novo jogo iniciando reseta o estado escondido (overlay volta a aparecer).

### Opacidade (já existia — revalidar)
- [ ] Slider de opacidade aplica ao vivo no overlay e persiste.

## v1.0 — Configurações gerais

- [ ] "Ocultar de gravações e capturas": gravar com OBS/Xbox Game Bar → overlay invisível na
      gravação, visível na tela.
- [ ] "Iniciar com o Windows": logoff/logon → app sobe na bandeja sozinho.

## v1.1 — Auto-update de assets (PENDENTE)

- [ ] Apagar um sprite de `assets/champions/` e abrir o app → sprite rebaixado sozinho em
      segundos (log "Assets updated"/"already up to date").
- [ ] Editar `assets/data/version.txt` para uma versão antiga → app rebaixa o snapshot
      completo em background sem travar a UI.
- [ ] Janela de configurações mostra "Dados do patch: <versão>".

## v2.0 — Cooldowns autoajustáveis (PENDENTE)

- [ ] Practice Tool: comprar Botas Ionianas num bot inimigo → em até ~10 s o ponto AZUL
      aparece no retrato e o próximo clique na spell usa cooldown reduzido (~9% menor;
      Flash 300 s → ~273 s).
- [ ] Clique direito no retrato alterna Inspiração Cósmica (ponto AMARELO) → Flash com
      botas+runa ≈ 234 s (300/1,28). Conferir contra cronômetro.
- [ ] Roda do mouse sobre um timer em andamento ajusta ±5 s por clique da roda.
- [ ] "Compensação de clique atrasado" nas configurações (ex.: 5 s) → timer inicia já
      descontado.
- [ ] Smite: clique inicia 90 s (recarga real), não os 15 s do Data Dragon.
- [ ] Teleport após 10:00 de jogo: clique usa cooldown do Unleashed (330–240 s conforme o
      nível do inimigo — nível vem da API).
- [ ] VERIFICAR NO PATCH ATUAL (valores hardcoded, conferidos no wiki em 2026-06-11):
      Botas Ionianas = 10 de haste; Cosmic Insight = 18; Smite = 90 s; upgrade do TP = 10:00.

## v1.0 — Release autocontida

- [ ] `build_release.bat` gera `dist\EzSpellTracker\` (exe + `_internal\` + `assets\`).
- [ ] Smoke local: rodar o exe num shell com `set PATH=C:\Windows;C:\Windows\System32` e
      `set PYTHONPATH=` → bandeja sobe, settings abre, preview funciona, `logs\` e `config\`
      criados ao lado do exe.
- [ ] Critério real: copiar a pasta para máquina/VM/usuário Windows sem Python instalado e
      repetir o smoke.
