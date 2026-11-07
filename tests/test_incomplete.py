import json
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from torrt import toolbox
from torrt.base_rpc import TorrentStatus
from torrt.exceptions import TorrtRPCException
from torrt.trackers.rutor import RutorTracker
from torrt.utils import NotifierObjectsRegistry, TorrtConfig


def test_pending_saves_intent_before_submission(pending_environment: Callable[..., SimpleNamespace]) -> None:
    environment = pending_environment()
    add_torrent = environment.client.method_add_torrent.side_effect

    def inspect_submission(*args: object, **kwargs: object) -> None:
        saved = json.loads(TorrtConfig.USER_SETTINGS_FILE.read_text(encoding="utf-8"))
        operation = saved["incomplete"][environment.key]
        assert operation["torrent"]["magnet"] == environment.torrent.magnet
        assert operation["clients"][environment.client.alias]["stage"] == "waiting"
        assert set(saved["torrents"]) == {environment.old_hash}
        add_torrent(*args, **kwargs)

    environment.client.method_add_torrent.side_effect = inspect_submission

    assert environment.pending.process(environment.clients) == {}

    saved = TorrtConfig.load()
    assert set(saved["torrents"]) == {environment.old_hash}
    assert environment.pending.get_hashes() == {environment.old_hash, environment.torrent.hash}
    assert saved["incomplete"][environment.key]["clients"][environment.client.alias]["stage"] == "waiting"
    environment.client.method_remove_torrent.assert_not_called()

@pytest.mark.parametrize("remove_outdated", [False, True])
def test_pending_completes_after_metadata(
    pending_environment: Callable[..., SimpleNamespace], remove_outdated: bool,
) -> None:
    environment = pending_environment(exclusions=True, remove_outdated=remove_outdated)
    environment.pending.process(environment.clients)
    environment.client.method_apply_file_exclusions.assert_not_called()
    environment.client.states[environment.torrent.hash]["metadata_ready"] = True

    updated = environment.pending.process(environment.clients)

    assert updated == {environment.old_hash: environment.torrent.to_dict()}
    assert set(TorrtConfig.load()["torrents"]) == {environment.torrent.hash}
    assert not TorrtConfig.load()["incomplete"]
    environment.client.method_add_torrent.assert_called_once()
    environment.client.method_apply_file_exclusions.assert_called_once_with(
        TorrentStatus(environment.torrent.hash, metadata_ready=True), ["Release/skip.txt"],
    )
    expected_removals = [call(environment.old_hash)] if remove_outdated else []
    assert environment.client.method_remove_torrent.call_args_list == expected_removals

def test_pending_waits_for_all_clients(pending_environment: Callable[..., SimpleNamespace]) -> None:
    environment = pending_environment(client_count=2)
    environment.pending.process(environment.clients)
    environment.client.states[environment.torrent.hash]["metadata_ready"] = True

    assert environment.pending.process(environment.clients) == {}
    assert set(TorrtConfig.load()["torrents"]) == {environment.old_hash, environment.torrent.hash}

    other_client = environment.clients["client_1"]
    other_client.enabled = False
    other_client.states[environment.torrent.hash]["metadata_ready"] = True

    assert environment.pending.process(environment.clients) == {}

    other_client.enabled = True
    assert environment.pending.process(environment.clients) == {environment.old_hash: environment.torrent.to_dict()}
    environment.client.method_remove_torrent.assert_called_once_with(environment.old_hash)
    other_client.method_remove_torrent.assert_called_once_with(environment.old_hash)

@pytest.mark.parametrize("exclusions", [False, True])
@pytest.mark.parametrize("already_present", [False, True])
def test_initial_addition_saves_registration_without_metadata(
    pending_environment: Callable[..., SimpleNamespace], exclusions: bool, already_present: bool,
) -> None:
    environment = pending_environment(replacing=False, exclusions=exclusions)

    if already_present:
        environment.client.states[environment.torrent.hash] = {
            "hash": environment.torrent.hash, "metadata_ready": False,
        }

    assert environment.pending.process(environment.clients) == {}
    assert set(TorrtConfig.load()["torrents"]) == {environment.torrent.hash}
    assert bool(TorrtConfig.load()["incomplete"]) is exclusions

    if exclusions:
        environment.client.states[environment.torrent.hash]["metadata_ready"] = True
        assert environment.pending.process(environment.clients) == {}
        environment.client.method_apply_file_exclusions.assert_called_once_with(
            TorrentStatus(environment.torrent.hash, metadata_ready=True), ["Release/skip.txt"],
        )

    assert not TorrtConfig.load()["incomplete"]
    assert environment.client.method_add_torrent.call_count == (0 if already_present else 1)
    environment.client.method_remove_torrent.assert_not_called()

def test_initial_addition_saves_registration_before_metadata_error(
    pending_environment: Callable[..., SimpleNamespace],
) -> None:
    environment = pending_environment(replacing=False, exclusions=True)
    environment.client.method_get_torrent_status.side_effect = [None, TorrtRPCException("Status is unavailable")]

    assert environment.pending.process(environment.clients) == {}

    saved = TorrtConfig.load()
    assert saved["torrents"][environment.torrent.hash] == environment.torrent.to_dict()
    assert saved["incomplete"][environment.key]["clients"][environment.client.alias]["stage"] == "waiting"
    environment.client.method_add_torrent.assert_called_once()
    environment.client.method_apply_file_exclusions.assert_not_called()

def test_pending_recovers_lost_add_response(pending_environment: Callable[..., SimpleNamespace]) -> None:
    environment = pending_environment()
    add_torrent = environment.client.method_add_torrent.side_effect

    def accepted_without_response(*args: object, **kwargs: object) -> None:
        add_torrent(*args, **kwargs)
        raise TorrtRPCException("Add response was lost")

    environment.client.method_add_torrent.side_effect = accepted_without_response

    assert environment.pending.process(environment.clients) == {}
    assert environment.pending.process(environment.clients) == {}

    environment.client.states[environment.torrent.hash]["metadata_ready"] = True

    assert environment.pending.process(environment.clients) == {environment.old_hash: environment.torrent.to_dict()}
    environment.client.method_add_torrent.assert_called_once()

def test_pending_retries_only_after_confirming_absence(pending_environment: Callable[..., SimpleNamespace]) -> None:
    environment = pending_environment()
    add_torrent = environment.client.method_add_torrent.side_effect
    environment.client.method_add_torrent.side_effect = TorrtRPCException("Add response was lost")
    environment.pending.process(environment.clients)
    environment.client.method_add_torrent.assert_called_once()
    get_torrent_status = environment.client.method_get_torrent_status.side_effect
    environment.client.method_get_torrent_status.side_effect = TorrtRPCException("Status is unavailable")

    assert environment.pending.process(environment.clients) == {}

    environment.client.method_add_torrent.assert_called_once()
    environment.client.method_get_torrent_status.side_effect = get_torrent_status
    environment.client.method_add_torrent.side_effect = add_torrent

    assert environment.pending.process(environment.clients) == {}

    assert environment.client.method_add_torrent.call_count == 2
    assert environment.torrent.hash in environment.client.states
    assert set(TorrtConfig.load()["torrents"]) == {environment.old_hash}
    environment.client.method_remove_torrent.assert_not_called()

def test_pending_keeps_old_torrent_when_registration_write_fails(
    pending_environment: Callable[..., SimpleNamespace], monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = pending_environment()
    environment.pending.process(environment.clients)
    environment.client.states[environment.torrent.hash]["metadata_ready"] = True
    save_settings = TorrtConfig.save

    def fail_registration(config_class: type[TorrtConfig], settings: dict) -> None:

        if environment.torrent.hash in settings["torrents"]:
            raise OSError("Storage unavailable")

        save_settings(settings)

    monkeypatch.setattr(TorrtConfig, "save", classmethod(fail_registration))

    with pytest.raises(OSError, match="Storage unavailable"):
        environment.pending.process(environment.clients)

    assert set(TorrtConfig.load()["torrents"]) == {environment.old_hash}
    environment.client.method_remove_torrent.assert_not_called()

def test_pending_does_not_add_when_intent_cannot_be_saved(
    pending_environment: Callable[..., SimpleNamespace], monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = pending_environment(queue=False)
    monkeypatch.setattr(TorrtConfig, "save", Mock(side_effect=OSError("Storage unavailable")))

    with pytest.raises(OSError, match="Storage unavailable"):
        environment.pending.queue(environment.torrent, environment.options, old_hash=environment.old_hash)

    environment.client.method_add_torrent.assert_not_called()

def test_pending_rechecks_replacement_before_removing_old(pending_environment: Callable[..., SimpleNamespace]) -> None:
    environment = pending_environment()
    environment.pending.process(environment.clients)
    environment.client.states[environment.torrent.hash]["metadata_ready"] = True
    environment.client.method_remove_torrent.side_effect = TorrtRPCException("Cleanup failed")
    environment.pending.process(environment.clients)
    environment.client.method_remove_torrent.assert_called_once_with(environment.old_hash)
    environment.client.states.pop(environment.torrent.hash)
    environment.client.method_remove_torrent.reset_mock()

    assert environment.pending.process(environment.clients) == {}

    environment.client.method_remove_torrent.assert_not_called()
    environment.client.method_add_torrent.assert_called_once()
    assert environment.old_hash in TorrtConfig.load()["torrents"]

def test_pending_removal_is_durable_and_resumes(pending_environment: Callable[..., SimpleNamespace]) -> None:
    environment = pending_environment(client_count=2)
    environment.pending.process(environment.clients)
    environment.client.method_remove_torrent.side_effect = TorrtRPCException("Client unavailable")

    toolbox.remove_torrent(environment.old_hash, with_data=True)

    operation = TorrtConfig.load()["incomplete"][environment.key]
    assert operation["cancelled"] is True
    assert operation["remove_with_data"] is True
    assert environment.old_hash in TorrtConfig.load()["torrents"]
    environment.client.method_remove_torrent.side_effect = (
        lambda hash_str, **kwargs: environment.client.states.pop(hash_str)
    )
    environment.client.method_remove_torrent.reset_mock()

    assert toolbox.check_incomplete_ops() == {}

    assert not TorrtConfig.load()["incomplete"]
    assert not TorrtConfig.load()["torrents"]
    assert environment.client.method_remove_torrent.call_args_list == [
        call(environment.torrent.hash, with_data=False), call(environment.old_hash, with_data=True),
    ]
    environment.client.method_add_torrent.assert_called_once()

@pytest.mark.parametrize("during_add", [False, True])
def test_unregister_during_rpc_does_not_restore_subscription(
    pending_environment: Callable[..., SimpleNamespace], during_add: bool,
) -> None:
    environment = pending_environment()
    method_name = "method_add_torrent" if during_add else "method_get_torrent_status"
    method = getattr(environment.client, method_name)
    original = method.side_effect

    def unregister_during_call(*args: object, **kwargs: object) -> object:
        toolbox.unregister_torrent(environment.old_hash)
        return original(*args, **kwargs)

    method.side_effect = unregister_during_call

    assert environment.pending.process(environment.clients) == {}

    assert not TorrtConfig.load()["incomplete"]
    assert not TorrtConfig.load()["torrents"]
    environment.client.method_remove_torrent.assert_not_called()

@pytest.mark.parametrize("method_name", [
    "method_get_torrent_status", "method_add_torrent", "method_apply_file_exclusions", "method_remove_torrent",
])
def test_pending_preserves_settings_changed_during_rpc(
    pending_environment: Callable[..., SimpleNamespace], method_name: str,
) -> None:
    environment = pending_environment(exclusions=True)
    method = getattr(environment.client, method_name)
    original = method.side_effect

    def change_preference(*args: object, **kwargs: object) -> object:
        TorrtConfig.update({"prefer_magnet": True, "custom": {"preserve": True}})

        if original is not None:
            return original(*args, **kwargs)

        return None

    method.side_effect = change_preference
    environment.pending.process(environment.clients)
    environment.client.states[environment.torrent.hash]["metadata_ready"] = True
    environment.pending.process(environment.clients)

    assert TorrtConfig.load()["prefer_magnet"] is True
    assert TorrtConfig.load()["custom"] == {"preserve": True}
    assert not TorrtConfig.load()["incomplete"]

@pytest.mark.parametrize("request_removal", [False, True])
@pytest.mark.parametrize("rpc_phase", ["add", "exclusions", "old_status"])
def test_cancellation_during_rpc_stops_replacement(
    pending_environment: Callable[..., SimpleNamespace], request_removal: bool, rpc_phase: str,
) -> None:
    environment = pending_environment(exclusions=True)
    methods = {
        "add": "method_add_torrent", "exclusions": "method_apply_file_exclusions",
        "old_status": "method_get_torrent_status",
    }

    if rpc_phase != "add":
        environment.pending.process(environment.clients)
        environment.client.states[environment.torrent.hash]["metadata_ready"] = True

    method = getattr(environment.client, methods[rpc_phase])
    original = method.side_effect

    def cancel_during_call(*args: object, **kwargs: object) -> object:

        if rpc_phase == "old_status" and args[0] != environment.old_hash:
            return original(*args, **kwargs)

        method.side_effect = original

        if request_removal:
            environment.pending.request_removal(environment.old_hash)

        else:
            toolbox.unregister_torrent(environment.old_hash)

        if original is not None:
            return original(*args, **kwargs)

        return None

    method.side_effect = cancel_during_call

    assert environment.pending.process(environment.clients) == {}

    environment.client.method_remove_torrent.assert_not_called()

    if request_removal:
        assert TorrtConfig.load()["incomplete"][environment.key]["cancelled"] is True
        assert environment.pending.process(environment.clients) == {}

    assert not TorrtConfig.load()["incomplete"]
    assert not TorrtConfig.load()["torrents"]
    environment.client.method_add_torrent.assert_called_once()

@pytest.mark.parametrize("rpc_phase", ["old_status", "exclusions"])
def test_replacement_disappearing_during_rpc_keeps_old(
    pending_environment: Callable[..., SimpleNamespace], rpc_phase: str,
) -> None:
    environment = pending_environment(exclusions=True)
    environment.pending.process(environment.clients)
    environment.client.states[environment.torrent.hash]["metadata_ready"] = True
    original_status = environment.client.method_get_torrent_status.side_effect

    def disappear_during_probe(hash_str: str) -> TorrentStatus | None:

        if hash_str == environment.old_hash:
            environment.client.states.pop(environment.torrent.hash)

        return original_status(hash_str)

    if rpc_phase == "old_status":
        environment.client.method_get_torrent_status.side_effect = disappear_during_probe

    else:
        environment.client.method_apply_file_exclusions.side_effect = lambda *args: environment.client.states.pop(
            environment.torrent.hash,
        )

    assert environment.pending.process(environment.clients) == {}

    environment.client.method_remove_torrent.assert_not_called()
    assert environment.old_hash in TorrtConfig.load()["torrents"]

def test_walk_finishes_pending_inside_postponed_interval(
    pending_environment: Callable[..., SimpleNamespace], monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = pending_environment()
    environment.pending.process(environment.clients)
    environment.client.states[environment.torrent.hash]["metadata_ready"] = True
    TorrtConfig.update({"time_last_check": 1_700_000_000, "walk_interval_hours": 24})
    monkeypatch.setattr(toolbox, "time", Mock(return_value=1_700_000_010))
    notifier = SimpleNamespace(alias="review", send=Mock())
    NotifierObjectsRegistry.add(notifier)

    toolbox.walk()

    assert not TorrtConfig.load()["incomplete"]
    assert TorrtConfig.load()["time_last_check"] == 1_700_000_000
    environment.client.method_get_torrents.assert_not_called()
    environment.client.method_add_torrent.assert_called_once()
    notifier.send.assert_called_once_with({environment.old_hash: environment.torrent.to_dict()})

@pytest.mark.parametrize("forced", [False, True])
def test_walk_retries_missing_submissions_once_per_run(
    pending_environment: Callable[..., SimpleNamespace], monkeypatch: pytest.MonkeyPatch,
    forced: bool,
) -> None:
    environment = pending_environment()
    environment.client.method_add_torrent.side_effect = TorrtRPCException("Add response was lost")
    environment.pending.process(environment.clients)
    TorrtConfig.update({"time_last_check": 1_700_000_000, "walk_interval_hours": 24})
    monkeypatch.setattr(toolbox, "time", Mock(return_value=1_700_000_010))

    toolbox.walk(forced=forced)

    assert environment.client.method_add_torrent.call_count == 2

    toolbox.walk(forced=forced)

    assert environment.client.method_add_torrent.call_count == 3
    assert environment.key in TorrtConfig.load()["incomplete"]
    assert set(TorrtConfig.load()["torrents"]) == {environment.old_hash}
    assert environment.client.method_get_torrents.call_count == (2 if forced else 0)
    environment.client.method_remove_torrent.assert_not_called()

def test_walk_discovers_all_clients_before_adding_magnet(
    pending_environment: Callable[..., SimpleNamespace], monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = pending_environment(client_count=2, queue=False, exclusions=True)
    extract_torrent = Mock(return_value=environment.torrent)
    monkeypatch.setattr(toolbox, "get_torrent_from_url", extract_torrent)

    for alias, client in environment.clients.items():
        client.method_get_torrents.return_value = [{
            "hash": environment.old_hash, "name": "Old release", "comment": "",
            **environment.options[alias],
        }]

    toolbox.walk(forced=True)

    extract_torrent.assert_called_once()
    operation = TorrtConfig.load()["incomplete"][environment.key]
    assert operation["torrent"]["magnet"] == environment.torrent.magnet
    assert set(operation["clients"]) == set(environment.clients)
    assert set(TorrtConfig.load()["torrents"]) == {environment.old_hash}

    for alias, client in environment.clients.items():
        client.method_add_torrent.assert_called_once()
        assert client.method_add_torrent.call_args.args[0].to_dict() == environment.torrent.to_dict()
        assert client.method_add_torrent.call_args.kwargs == environment.options[alias]
        client.method_remove_torrent.assert_not_called()

def test_add_from_url_queues_magnet_with_parameters(
    pending_environment: Callable[..., SimpleNamespace], monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = pending_environment(replacing=False, queue=False)
    monkeypatch.setattr(toolbox, "get_torrent_from_url", Mock(return_value=environment.torrent))

    toolbox.add_torrent_from_url(environment.torrent.url, download_to="/downloads", params={"category": "Review"})

    saved = TorrtConfig.load()
    assert saved["torrents"][environment.torrent.hash]["params"] == {"category": "Review"}
    assert not saved["incomplete"]
    environment.client.method_add_torrent.assert_called_once()
    assert environment.client.method_add_torrent.call_args.args[0].to_dict() == environment.torrent.to_dict()
    assert environment.client.method_add_torrent.call_args.kwargs == {
        "download_to": "/downloads", "params": {"category": "Review"},
    }

def test_unchanged_magnet_does_not_probe_metadata(
    pending_environment: Callable[..., SimpleNamespace], monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = pending_environment(replacing=False, queue=False)
    toolbox.register_torrent(environment.torrent.hash, torrent_data=environment.torrent)
    environment.client.method_get_torrents.return_value = [{
        "hash": environment.torrent.hash, "name": "Unchanged release", "comment": "", "download_to": "/downloads",
    }]
    monkeypatch.setattr(toolbox, "get_torrent_from_url", Mock(return_value=environment.torrent))

    toolbox.walk(forced=True)

    assert not TorrtConfig.load()["incomplete"]
    environment.client.method_get_torrent_status.assert_not_called()
    environment.client.method_add_torrent.assert_not_called()
    environment.client.method_remove_torrent.assert_not_called()

def test_full_walk_refreshes_cached_magnet_page(
    pending_environment: Callable[..., SimpleNamespace], response_mock: Callable,
) -> None:
    environment = pending_environment(queue=False)
    tracker = RutorTracker()
    tracker.mirror_picked = tracker.alias
    tracker.register()
    url = f"https://{tracker.alias}/torrent/123"
    TorrtConfig.update({"prefer_magnet": True, "torrents": {environment.old_hash: {"url": url}}})
    environment.client.method_get_torrents.return_value = [{
        "hash": environment.old_hash, "name": "Old release", "comment": "", "download_to": "/downloads",
    }]
    next_hash = "c" * 40

    with response_mock([], bypass=False) as mocked:
        mocked.add("GET", url, body=f'<a href="{environment.torrent.magnet}">Magnet</a>')
        mocked.add("GET", url, body=f'<a href="magnet:?xt=urn:btih:{next_hash}">Magnet</a>')

        toolbox.walk(forced=True)
        environment.client.states[environment.torrent.hash]["metadata_ready"] = True
        environment.client.method_get_torrents.return_value[0]["hash"] = environment.torrent.hash
        toolbox.walk(forced=True)

        assert len(mocked.calls) == 2

    saved = TorrtConfig.load()
    assert set(saved["torrents"]) == {environment.torrent.hash}
    assert saved["incomplete"][environment.torrent.hash]["torrent"]["hash"] == next_hash
    assert environment.client.method_add_torrent.call_count == 2

def test_walk_does_not_start_replacement_with_unknown_client_targets(
    pending_environment: Callable[..., SimpleNamespace], monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = pending_environment(client_count=2, queue=False)
    environment.client.method_get_torrents.return_value = [{
        "hash": environment.old_hash, "name": "Old release", "comment": "", "download_to": "/downloads",
    }]
    environment.clients["client_1"].method_get_torrents.side_effect = TorrtRPCException("Client unavailable")
    extract_torrent = Mock(return_value=environment.torrent)
    monkeypatch.setattr(toolbox, "get_torrent_from_url", extract_torrent)

    with pytest.raises(TorrtRPCException, match="Client unavailable"):
        toolbox.walk(forced=True)

    extract_torrent.assert_not_called()
    assert not TorrtConfig.load()["incomplete"]
    assert set(TorrtConfig.load()["torrents"]) == {environment.old_hash}
    environment.client.method_add_torrent.assert_not_called()
