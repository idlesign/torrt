# torrt changelog

### Unreleased
* !! QA. Dropped QA for Py 3.7, 3.8, 3.9, 3.10.
* ++ Add support to pass custom RPC parameters.
* ++ QA. Added QA for Py 3.11.
* ** Trackers. Anilibria support suspended.

### v1.0.0 [2021-12-26]
* ++ Release. Celebrating 1.0.0.
* ++ Trackers. Added support for yts.mx tracker.
* ** RPC. Fixed qbittorrent torrent removal (fixes #72).
* ** Python. Now Python 3.10 compatible.

### v0.16.3 [2021-10-13]
* ** RPC. Fixed qbittorrent 'savepath' is not a valid torrent file (fix #71).

### v0.16.2 [2021-07-14]
* ++ RPC. uTorrent now supports download location setting.

### v0.16.1 [2021-04-20]
* ** Core. Now bogus torrent files errors are logged.

### v0.16.0 [2021-02-05]
* ++ Trackers. Added EniaHD tracker support.

### v0.15.2 [2021-01-31]
* ** Rutor. Fixed seo-URLs handling.

### v0.15.1 [2020-10-12]
* ** Anilibria. Fixed single-episode shows handling.

### v0.15.0 [2020-09-26]
* !! RPC. Support qBittorrent v4.1+ (previous API version support is dropped) (see #53). Please reconfigure RPC.
* ** CLI. Fix regression in 'register_torrent' (see #57).

### v0.14.1 [2020-08-30]
* ** Core. Fix torrent page caching issue (see #56).

### v0.14.0 [2020-08-01]
* !! QA. Dropped QA for Python 3.5. Added QA for 3.8.
* !! Python. Dropped support for Python 2.
* ++ CLI. Add --dump switch for 'add_torrent' command.
* ++ Trackers. Add mirrors for casstudio and kinozal (see #55).
* ++ Trackers. Added tools to extract additional information from torrent pages.
* ++ RPC. Try to preserve list of excluded files.
* ** Anilibria. Improved series range picking.
* ** RPC. Fixed automatic RPC enable on configuration.

### v0.13.1 [2020-02-16]
* ** Anilibria. Switched to API.
* ** RPC. Fixed Transmission RPC 'add_torrent()' regression.

### v0.13.0 [2019-09-22]
* ++ Bots. Telegram bots. Batch messages for /list command.
* ** Anilibria. Qualities picking related changes.
* ** Python. Py2/3 compat improvements.

### v0.12.0
* ++ Bots. New commands for Telegram bot.
* ** CasStudio. Improved tracker support.

### v0.11.1
* ** CasStudio. Fixed tracker support.

### v0.11.0
* ++ Trackers. Added CasStudio tracker support.
* ++ Bots. Bots subsystem added featuring Telegram bot.
* ++ Core. Public tracker registration made optional.
* ** Anilibria. AniLibria.tv new page layout adoption and quality picker improvements.
* ** Notifiers. Telegram notifier improved.

### v0.10.1
* ** Python. Py3 compatibility improvements.

### v0.10.0
* ++ Trackers. Added AniLibria tracker.

### v0.9.1
* ** Python. Py3 compatibility improved.

### v0.9.0
* ** Rutracker. Fixed another rutracker login issue.
* ++ RPC. QBittorrent RPC support.

### v0.8.0
* ++ Trackers. Added kinozal.tv tracker.
* ++ Python. Basic Python 3 support.

### v0.7.1
* ** Rutracker. Fixed rutracker login issue.

### v0.7.0
* ++ RPC. Deluge plugin updated.
* ++ Trackers. Rutor plugin updated.

### v0.6.0
* ** Trackers. rutracker mirror list updated.
* ** Trackers. nnm club mirror list updated.
* ++ Core. Implemented mirror domain availability discovery.

### v0.5.0
* !! RPC. Torrent parsing switched from `libtorrent` to `torrentool`.
* ++ CLI. Launcher script is now crossplatform.
* ** CLI. `torrt walk` output made less verbose and more structured.

### v0.4.2
* ** Core. Torrents without URL in comment won't issue exceptions anymore.
* ++ Core. Added request timeout, defaults to 10 sec.
* !! Dependencies. HTML parsing now requires `lxml` module.
* ** CLI. `--verbose` option now works with all commands.

### v0.4.1
* ** Rutracker. Fixed rutracker torrents download.

### v0.4.0
* ++ Core. Implemented tracker mirrors support.
* ** CLI. --version command arg made py3 compatible.
* ** Rutracker. rutracker.org torrent file download fix.

### v0.3.0
* ++ Notifiers. Implemented Notifications subsystem.
* !! API. get_registerd_torrents() is deprecated in favor of get_registered_torrents().

### v0.2.3
* ** Walk. Now removes outdated torrents from torr when walking.

### v0.2.2
* ** CLI. Now less verbose.
* ** Walk. Now removes outdated torrents from clients when walking from CLI.

### v0.2.1
* ++ CLI. `list_rpc` console command now shows statuses.
* ** Trackers. Fixed nnm-club tracker auth procedures.
* ** Walk. Walk mechanics improved.

### v0.2.0
* ++ RPC. Implemented uTorrent crippled RPC support.

### v0.1.0
* ++ Core. Basic functionality.