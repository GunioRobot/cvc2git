Tool to convert a conary repository to a git repository

License: GPLv2

Usage
=====

Two scripts are provided: `get-all-pkg-log`, `cvc2git.py`. The first is to fetch
the logs of the packages into a cache dir, then the second can use the cache
and build a git repo out of it. I haven't managed to make the scripts too
fancy, so you have to manually combine the two scripts as proper.

    $ cachedir="/tmp/cvc-history"
    $ gitdir="/tmp/cvc2git/"
    $ label="foresight.rpath.org@fl:2-devel"
    $
    $ ./get-all-pkg-log "$label" "$cachedir"
    $ cat "$cachedir"/sources-list | cut -d: -f1 | xargs ./cvc2git.py --history-dir="$cachedir"/logs --git-dir="$gitdir"

You could save these to a helper script, as the `example-*` scripts do.

More
====

A tip on git. If you want to put the different branches in the same repo (as
done at https://github.com/foresight/legacy/), use `git checkout --orphan`.

Fetch 'cvc log' for one package:

    # ./get-pkg-log zenity:source=foresight.rpath.org@fl:1-devel > some/file

Pick packages to convert:

    $ ./cvc2git.py --history-dir=/tmp/cvc-history/logs --git-dir=/tmp/cvc2git/ pilot-link rapid-photo-downloader rapidsvn raptor group-desktop-platform

Refresh the git repo:

    $ cat /tmp/cvc-history/sources-list | cut -d: -f1 | xargs ./cvc2git.py --history-dir=/tmp/cvc-history/logs --git-dir=/tmp/cvc2git/

TODO
====
 - Wrap all these commands and hide implementation details
