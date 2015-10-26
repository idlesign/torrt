Console application commands
============================

Those are **torrt** console application commands:


Trackers
--------

* **list_trackers** - Shows known trackers aliases

* **configure_tracker** - Sets torrent tracker settings (login credentials, etc.)


PRCs
----

* **list_rpc** - Shows known RPCs aliases

* **configure_rpc** - Sets RPCs settings (login credentials, etc.)

* **enable_rpc** - Enables RPC by its alias

* **disable_rpc** - Disables RPC by its alias


Torrents
--------

* **add_torrent** - Adds torrent from an URL both to *torrt* and torrent clients

* **remove_torrent** - Removes torrent by its hash both from *torrt* and torrent clients

* **register_torrent** - Registers torrent within *torrt* by its hash (for torrents already existing at torrent clients)

* **unregister_torrent** - Unregisters torrent from *torrt* by its hash


Notifications
-------------

* **configure_notifier** - Sets notification settings (SMTP server or telegram bot ID)

* **remove_notifier** - Remove notifier from *torrt* by its hash


Update procedure
----------------

* **walk** - Walks through registered torrents and performs automatic updates

* **set_walk_interval** - Sets an interval *in hours* between consecutive torrent updates checks



.. note::

    More information on commands supported by **torrt** console application is available through `--help` command line switch

