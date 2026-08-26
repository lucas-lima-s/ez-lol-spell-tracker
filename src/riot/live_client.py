import logging
from pathlib import Path

import requests

from src.core.paths import RIOT_CERT_FILE

logger = logging.getLogger(__name__)

LIVE_CLIENT_BASE_URL = "https://127.0.0.1:2999/liveclientdata"
CONNECT_TIMEOUT = 0.5
READ_TIMEOUT = 2.0


class LiveClientError(Exception):
    pass


class NotInGameError(LiveClientError):
    pass


class TransientApiError(LiveClientError):
    pass


class LiveClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        base_url: str = LIVE_CLIENT_BASE_URL,
        cert_file: Path = RIOT_CERT_FILE,
    ) -> None:
        if not cert_file.is_file():
            raise FileNotFoundError(f"Riot certificate not found: {cert_file}")
        if session is None:
            session = requests.Session()
            session.trust_env = False
        self._session = session
        self._base_url = base_url
        self._cert_file = cert_file
        self._ssl_warned = False

    def _get(self, endpoint: str) -> dict:
        url = f"{self._base_url}/{endpoint}"
        try:
            response = self._session.get(
                url,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                verify=str(self._cert_file),
            )
        except requests.exceptions.SSLError as exc:
            if self._ssl_warned:
                logger.debug("TLS verification failed for %s: %s", url, exc)
            else:
                self._ssl_warned = True
                logger.warning(
                    "TLS verification failed for %s; riotgames.pem may have rotated: %s",
                    url,
                    exc,
                )
            raise TransientApiError(str(exc)) from exc
        except requests.exceptions.ConnectTimeout as exc:
            raise TransientApiError(str(exc)) from exc
        except requests.exceptions.ConnectionError as exc:
            raise NotInGameError(str(exc)) from exc
        except requests.exceptions.Timeout as exc:
            raise TransientApiError(str(exc)) from exc
        except requests.exceptions.RequestException as exc:
            raise TransientApiError(str(exc)) from exc
        if response.status_code != 200:
            raise TransientApiError(f"HTTP {response.status_code} from {endpoint}")
        try:
            return response.json()
        except ValueError as exc:
            raise TransientApiError(f"Invalid JSON from {endpoint}") from exc

    def get_game_stats(self) -> dict:
        return self._get("gamestats")

    def get_all_game_data(self) -> dict:
        return self._get("allgamedata")

    def is_in_game(self) -> bool:
        try:
            self.get_game_stats()
        except LiveClientError:
            return False
        return True
