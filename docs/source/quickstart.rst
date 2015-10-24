Quickstart
==========

In this examples we'll use console commands.

1. **torrt** cooperates with actual torrent clients (through RPC), so we need to tell it how to connect to them.

  Let's configure Transmission (https://www.transmissionbt.com/) connection (considering Transmission web interface is on 192.168.1.5)::

    > torrt configure_rpc transmission host=192.168.1.5 user=idle password=pSW0rt

  To get known RPCs aliases use `list_rpc` command.


2. Second step is to tell **torrt** how to authorize into private torrent trackers.

  Let's configure authorization for http://rutracker.org tracker::

   > torrt configure_tracker rutracker.org username=idle password=pSW0rt

  To get known tracker aliases use `list_trackers` command.


3. Now let's subscribe to torrent updates, say from http://rutracker.org/forum/viewtopic.php?t=4430338::

    > torrt add_torrent http://rutracker.org/forum/viewtopic.php?t=4430338

  To get torrents registered for updates use `list_torrents` command.

4. Configure notifications about torrent updates.

  Let's configure notifications through email::

    > torrt configure_notifier email host=smtp.server.com port=25 use_tls=True email=your@email.com user=idle password=pSW0rt


5. Updates checks for torrents registered within **torrt** can be done with `walk` command::

    > torrt walk


6. Use `set_walk_interval` command to set walk interval in hours::

    > torrt set_walk_interval 24


.. note::

    More information on commands supported by **torrt** console application is available through `--help` command line switch::

      > torrt --help
      > torrt configure_rpc --help
      > torrt add_torrent --help
