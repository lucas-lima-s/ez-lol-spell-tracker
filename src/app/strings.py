STRINGS = {
    "app.name": "EzSpellTracker",
    "tray.tooltip": "EzSpellTracker",
    "menu.settings": "Configurações",
    "menu.show_overlay": "Mostrar overlay",
    "menu.exit": "Sair",
    "settings.title": "EzSpellTracker — Configurações",
    "error.already_running.title": "EzSpellTracker",
    "error.already_running.text": "O EzSpellTracker já está em execução.",
    "error.no_tray.title": "EzSpellTracker",
    "error.no_tray.text": ("Bandeja do sistema indisponível. O aplicativo não pode iniciar."),
    "error.startup.title": "EzSpellTracker",
    "error.startup.text": (
        "Falha ao iniciar: arquivos de dados ausentes ou corrompidos. "
        "Reinstale o aplicativo ou rode scripts/fetch_assets.py."
    ),
    "settings.group.overlay": "Overlay",
    "settings.group.general": "Geral",
    "settings.scale": "Escala",
    "settings.opacity": "Opacidade",
    "settings.locked": "Bloquear posição do overlay",
    "settings.reset_position": "Redefinir posição",
    "settings.hide_from_capture": "Ocultar de gravações e capturas",
    "settings.hide_from_capture_unsupported": ("Indisponível nesta versão do Windows."),
    "settings.start_with_windows": "Iniciar com o Windows",
    "settings.start_with_windows_failed": ("Não foi possível alterar a inicialização automática."),
    "settings.help.controls": (
        "Clique esquerdo no ícone inicia o timer; clique direito reseta. "
        "Roda do mouse sobre o ícone ajusta o timer em ±5 s. "
        "Clique direito no retrato alterna a runa Inspiração Cósmica do inimigo "
        "(ponto amarelo); Botas Ionianas são detectadas sozinhas (ponto azul). "
        "Arraste o painel para reposicionar (com a posição destravada). "
        "O cadeado no topo do overlay também trava/destrava a posição."
    ),
    "settings.cast_offset": "Compensação de clique atrasado (s)",
    "settings.resolution_profile": "Perfil de resolução atual:",
    "settings.data_version": "Dados do patch:",
    "settings.hotkey": "Atalho mostrar/ocultar overlay",
    "settings.hotkey_failed": ("Não foi possível registrar o atalho (em uso por outro programa?)."),
}


def tr(key: str) -> str:
    return STRINGS.get(key, key)
