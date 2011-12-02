Tool to convert a conary repository to a git repository

License: GPLv2

Usage
=====

    $ cvc2git.py --label=foresight.rpath.org@fl:2-devel --cachedir=/tmp/cvc2gitcache --git-dir=/tmp/gitrepo

The command can be safely rerun; it will reuse the cache and the git repo.

More
====

* Options:

        --no-refresh    If specified, will not refresh the cache at cachedir

* If a list of packages are specified explicitly, cvc2git will only convert these:

        $ cvc2git.py --cachedir=/tmp/cvc-history/ --git-dir=/tmp/gitrepo/ pkgfoo pkgbar pkgmore

* The two utility scripts can be used standalone.

* get-all-pkg-log - fetch 'cvc log' for all packages on a label

        $ get-all-pkg-log foresight.rpath.org@fl:2-devel /tmp/cvc2gitcache

* get-pkg-log - fetch 'cvc log' for one package:

        $ get-pkg-log zenity:source=foresight.rpath.org@fl:1-devel > some/file

Others
======

A tip on git. If you want to put the different branches in the same repo (as
done at https://github.com/foresight/legacy/), use `git checkout --orphan`.
