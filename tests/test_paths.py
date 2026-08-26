from src.core import paths


def test_project_root_is_repo_root():
    assert (paths.PROJECT_ROOT / "pyproject.toml").is_file()
    assert (paths.PROJECT_ROOT / "run.bat").is_file()


def test_all_paths_are_children_of_root():
    children = (
        paths.CONFIG_DIR,
        paths.SETTINGS_FILE,
        paths.LOGS_DIR,
        paths.ASSETS_DIR,
        paths.TRAY_ICON_FILE,
        paths.CHAMPIONS_DIR,
        paths.SPELLS_DIR,
        paths.DATA_DIR,
        paths.SUMMONER_DATA_FILE,
        paths.CHAMPIONS_DATA_FILE,
        paths.DATA_VERSION_FILE,
        paths.RIOT_CERT_FILE,
    )
    for child in children:
        assert child.is_relative_to(paths.PROJECT_ROOT)
