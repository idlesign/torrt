"""Persist and complete magnet additions without waiting for peer metadata."""

import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Any, NamedTuple

from .exceptions import TorrtRPCException
from .utils import TorrentData, TorrtConfig

if TYPE_CHECKING:
    from .base_rpc import BaseRPC

LOGGER = logging.getLogger(__name__)

class TargetState(NamedTuple):
    """Keep one client's progress together with the configuration it came from."""

    key: str
    alias: str
    settings: dict[str, Any]
    operation: dict[str, Any]
    target: dict[str, Any]

class IncompleteOps:
    """Keep recoverable, per-client progress in the application configuration."""

    def __init__(self, settings: type[TorrtConfig]) -> None:
        self.settings = settings

    def queue(
        self, torrent: TorrentData, clients: dict[str, dict[str, Any]], *,
        old_hash: str = "", remove_outdated: bool = True,
    ) -> str:
        """Save an addition intent before making any changes to torrent clients."""

        if not torrent.magnet or not clients or old_hash == torrent.hash:
            raise ValueError("An incomplete magnet operation needs a new hash and at least one client")

        key = old_hash or f"add:{torrent.hash}"
        settings = self.settings.load()
        pending = settings["incomplete"]

        if key in pending:
            return key

        pending[key] = {
            "old_hash": old_hash,
            "torrent": torrent.to_dict(),
            "remove_outdated": remove_outdated,
            "clients": {
                alias: {**deepcopy(options), "stage": "waiting"}
                for alias, options in clients.items()
            },
        }
        self.settings.save(settings)
        return key

    def get_hashes(self) -> set[str]:
        """Return hashes already involved in an unfinished addition or replacement."""
        hashes = set()

        for pending in self.settings.load()["incomplete"].values():
            hashes.add(pending["torrent"]["hash"])

            if pending["old_hash"]:
                hashes.add(pending["old_hash"])

        return hashes

    def cancel(self, hash_str: str) -> list[dict[str, Any]]:
        """Stop following a subscription and its unfinished replacement."""
        settings = self.settings.load()
        cancelled = []

        for key, pending in list(settings["incomplete"].items()):

            if hash_str not in (pending["old_hash"], pending["torrent"]["hash"]):
                continue

            cancelled.append(pending)
            settings["incomplete"].pop(key)
            settings["torrents"].pop(pending["old_hash"], None)
            settings["torrents"].pop(pending["torrent"]["hash"], None)

        settings["torrents"].pop(hash_str, None)
        self.settings.save(settings)
        return cancelled

    def request_removal(self, hash_str: str, *, with_data: bool = False) -> bool:
        """Save a cancellation before removing a pending operation's client torrents."""
        settings = self.settings.load()
        found = False

        for pending in settings["incomplete"].values():

            if hash_str not in (pending["old_hash"], pending["torrent"]["hash"]):
                continue

            found = True
            pending["cancelled"] = True
            pending["remove_hash"] = hash_str
            pending["remove_with_data"] = with_data

            for target in pending["clients"].values():
                target["stage"] = "removing"

        if found:
            self.settings.save(settings)

        return found

    def process(self, clients: dict[str, "BaseRPC"], *, keys: set[str] | None = None) -> dict[str, dict]:
        """Advance selected operations, resubmitting only torrents confirmed absent."""
        updated = {}

        for key, pending in list(self.settings.load()["incomplete"].items()):

            if keys is not None and key not in keys:
                continue

            torrent_hash = pending["torrent"]["hash"]

            for alias in pending["clients"]:
                client = clients.get(alias)

                if client is None or not client.enabled:
                    continue

                state = self._load_target(key, alias, torrent_hash=torrent_hash)

                if state is None:
                    continue

                try:
                    self._advance(client, state)

                except TorrtRPCException as error:
                    LOGGER.error("Incomplete operation %s in %s failed: %s", key, alias, error)

            settings = self.settings.load()
            pending = settings["incomplete"].get(key)

            if pending is None or pending["torrent"]["hash"] != torrent_hash:
                continue

            if any(target["stage"] != "done" for target in pending["clients"].values()):
                continue

            old_hash = pending["old_hash"]
            torrent = pending["torrent"]

            if pending.get("cancelled"):
                settings["torrents"].pop(old_hash, None)
                settings["torrents"].pop(torrent["hash"], None)

            elif old_hash:
                settings["torrents"].pop(old_hash, None)
                updated[old_hash] = torrent

            settings["incomplete"].pop(key)
            self.settings.save(settings)

        return updated

    def _load_target(self, key: str, alias: str, *, torrent_hash: str) -> TargetState | None:
        settings = self.settings.load()
        pending = settings["incomplete"].get(key)

        if pending is None or pending["torrent"]["hash"] != torrent_hash:
            return None

        target = pending["clients"].get(alias)

        if target is None:
            return None

        return TargetState(key=key, alias=alias, settings=settings, operation=pending, target=target)

    def _reload_target(self, previous: TargetState) -> TargetState | None:
        """Recheck progress after RPC without reviving cancelled or superseded work."""
        state = self._load_target(previous.key, previous.alias, torrent_hash=previous.operation["torrent"]["hash"])

        if state is None or state.target["stage"] != previous.target["stage"]:
            return None

        if bool(state.operation.get("cancelled")) != bool(previous.operation.get("cancelled")):
            return None

        return state

    def _advance(self, client: "BaseRPC", state: TargetState) -> None:
        """Dispatch one client's work using the already loaded progress."""

        if state.target["stage"] == "done":
            return

        if state.operation.get("cancelled"):
            self._advance_removal(client, state)
            return

        if state.target["stage"] != "ready":
            state = self._prepare_torrent(client, state)

            if state is None:
                return

        self._finish_client(client, state)

    def _advance_removal(self, client: "BaseRPC", state: TargetState) -> None:
        """Finish a saved removal without restoring progress cancelled during RPC."""
        torrent_hash = state.operation["torrent"]["hash"]

        for hash_str in (torrent_hash, state.operation["old_hash"]):

            if not hash_str:
                continue

            status = client.method_get_torrent_status(hash_str)

            if (state := self._reload_target(state)) is None:
                return

            if status is not None:
                client.method_remove_torrent(
                    hash_str,
                    with_data=state.operation["remove_with_data"] and hash_str == state.operation["remove_hash"],
                )

                if (state := self._reload_target(state)) is None:
                    return

        state.target["stage"] = "done"
        self.settings.save(state.settings)

    def _save_registration(self, state: TargetState, *, stage: str) -> None:
        """Save registration and progress together, skipping an unchanged metadata wait."""
        torrent = state.operation["torrent"]

        if state.target["stage"] == stage and state.settings["torrents"].get(torrent["hash"]) == torrent:
            return

        state.settings["torrents"][torrent["hash"]] = torrent
        state.target["stage"] = stage
        self.settings.save(state.settings)

    def _prepare_torrent(self, client: "BaseRPC", state: TargetState) -> TargetState | None:
        """Ensure acceptance and save readiness once metadata and exclusions are ready."""
        torrent = TorrentData.from_dict(state.operation["torrent"])
        excluded_names = [
            name for name, options in (state.target.get("params") or {}).get("files", {}).items()
            if options.get("exclude", False)
        ]
        status = client.method_get_torrent_status(torrent.hash)

        if (state := self._reload_target(state)) is None:
            return None

        if status is None:
            LOGGER.info("Torrent %s is absent from %s; submitting the saved magnet", torrent.hash, state.alias)
            # The waiting intent is already durable; a lost response is resolved by the next status query.
            client.method_add_torrent(
                torrent, download_to=state.target.get("download_to", ""), params=state.target.get("params"),
            )

            if (state := self._reload_target(state)) is None:
                return None

        if not state.operation["old_hash"]:
            self._save_registration(state, stage="waiting" if excluded_names else "done")

            if not excluded_names:
                return None

        if status is None:
            status = client.method_get_torrent_status(torrent.hash)

            if (state := self._reload_target(state)) is None:
                return None

        if status is None or not status.metadata_ready:
            LOGGER.info("Waiting for metadata for %s in %s", torrent.hash, state.alias)
            return None

        if excluded_names:
            client.method_apply_file_exclusions(status, excluded_names)

            if (state := self._reload_target(state)) is None:
                return None

        self._save_registration(state, stage="ready")
        return state

    def _finish_client(self, client: "BaseRPC", state: TargetState) -> None:
        """Recheck the prepared replacement before removing the old client torrent."""
        old_hash = state.operation["old_hash"]
        torrent_hash = state.operation["torrent"]["hash"]
        old_status = None

        if old_hash and state.operation["remove_outdated"]:
            old_status = client.method_get_torrent_status(old_hash)

            if (state := self._reload_target(state)) is None:
                return

        # Metadata can disappear after an earlier probe or while exclusions are applied.
        status = client.method_get_torrent_status(torrent_hash)

        if (state := self._reload_target(state)) is None:
            return

        if status is None or not status.metadata_ready:
            LOGGER.warning(
                "Replacement %s in %s is no longer ready; keeping the old torrent", torrent_hash, state.alias,
            )
            return

        if old_status is not None and state.operation["remove_outdated"]:
            client.method_remove_torrent(old_hash)

            if (state := self._reload_target(state)) is None:
                return

        state.target["stage"] = "done"
        self.settings.save(state.settings)
