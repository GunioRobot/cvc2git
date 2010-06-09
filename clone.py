from commands import getstatusoutput
import os
import sys

from utils import (
        commit_to_git,
        init_git_repository,
        parse_history,
        )

def _parse_package_name(full_version):
    '''Parse package name from a full version string'''
    s = full_version.split("=", 1)[0]
    if ":" in s: # this is a trove name, like 'pkg:source'
        return s.split(":", 1)[0]
    return s

def _checkout(trove, dest):
    if not dest:
        dest = _parse_package_name(trove)
    if os.path.isdir(dest) and os.listdir(dest):
        print "Error: directory %s already exists and is not empty" % dest
        sys.exit()

    print "checking out %s to %s" % (trove, dest)
    s = getstatusoutput("cvc checkout --dir=%s %s" % (dest, trove))
    if s[0] != 0:
        print "cvc co fails:", s[1]
        sys.exit()
    return dest

def do_clone(trove, dest=None):
    workdir = _checkout(trove, dest)

    # change to work directory
    os.chdir(workdir)
    revisions = parse_history()

    if not init_git_repository():
        return
    commit_to_git(revisions)
    print "done"
