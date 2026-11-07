# Magnet links

To prefer magnet links over downloading `.torrent` files:

```shell
torrt set_prefer_magnet true
```

The setting applies to the console, bots and automatic updates. It is disabled by default;
use `torrt set_prefer_magnet false` to restore the default.

Keep using the torrent's tracker page URL with `add_torrent`. Direct magnet subscriptions
are not supported: the page URL is needed to discover future updates.

## Supported sources and clients

Magnet extraction is implemented for RuTracker, NNM-Club, EniaHD and Rutor.
Each tracker explicitly opts in and can customize how it finds the link.
The fetched page is reused for link extraction, title and other page information.
Trackers without an extractor, pages without a magnet, and invalid magnets use the
existing `.torrent` download path.

Transmission, Deluge, qBittorrent and uTorrent accept extracted magnets through
their native APIs. No `.torrent` file is downloaded by torrt for a valid preferred
magnet, even when its file list is not yet known.

BitTorrent v1 magnets are supported, including hexadecimal and base32 BTIH hashes.
Pure v2 magnets are not currently supported. The complete link, including repeated
tracker parameters, is preserved. The display name comes from `dn`, then the page
title, then the hash.

## Saved progress and recovery

Before submitting a magnet, torrt atomically saves an operation under `incomplete`
in `~/.torrt/config.json`: the link, hash, page information, old hash and per-client
destination, parameters and progress. The configuration file is private to its owner;
it can contain private tracker passkeys, so protect its backups as well.

Diagnostics are not redacted. Request URLs, error messages and the original response
bodies saved by `--dump` can contain passkeys or authentication tokens. Review them
before sharing.

New subscriptions are saved as soon as the client accepts the magnet; no metadata
wait is needed unless file exclusions must be applied. Replacements keep the old
subscription and client torrent until the new metadata is available, exclusions are
applied and the new subscription is saved. The old client torrent is then removed
without deleting downloaded data. An update spanning multiple clients completes only
after every recorded client finishes. Disabled or missing clients leave it pending.

To record all replacement targets safely, discovery must succeed for every enabled
client before a full walk starts new replacements. If one is unavailable, new
replacements are deferred; already saved operations can still progress in the
other clients. This also makes multi-client `.torrent` updates more conservative
than before.

Torrt does not wait for peers during a walk. Each run first checks the client's current
metadata state and continues saved operations without downloading their pages again:

```shell
torrt walk
```

Pending operations are checked even when the ordinary tracker-check interval has
not elapsed. Only a due or forced walk checks tracker pages for new updates.
Run `walk` regularly, for example every few minutes from your scheduler;
torrt does not start a background worker itself.

If a submission's response was lost, torrt first checks whether the client already
has the torrent. A successful check confirming its absence allows automatic
resubmission on the next `walk`, at most once per client and operation per run.
An existing torrent is not submitted again. If the status check fails, torrt leaves
the operation pending without resubmitting it. No retry option is required.

To abandon a pending addition, use `unregister_torrent` or `remove_torrent` in torrt.
Removing an unconfirmed addition only in the client can cause it to be submitted
again after torrt confirms its absence.

`unregister_torrent` cancels the related pending operation without removing client
torrents. `remove_torrent` saves removal intent and resumes unfinished cleanup on
subsequent checks. Run state-changing commands sequentially against one configuration;
atomic file replacement does not serialize concurrent processes.

## File exclusions

Transmission's existing excluded-file selection is preserved by file name after the
new magnet's metadata arrives. A changed file name does not match the old exclusion,
just as with `.torrent` updates. No torrent file is downloaded to obtain this list.
Other clients retain their existing parameter support; this does not add file-selection
preservation to adapters that did not support it before.

!!! warning
    Transmission starts the magnet before the deferred exclusions can be applied.
    Some excluded data may download in the meantime, especially if checks are infrequent.
    Its supported RPC has no reliable metadata-only mode. Torrt deliberately keeps
    using the magnet rather than silently switching to `.torrent`.
