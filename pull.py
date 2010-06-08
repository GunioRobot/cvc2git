from commands import getstatusoutput
import sys

from utils import (
        commit_to_git,
        parse_history,
        )

def read_local_version():
    '''Read current version from CONARY'''
    config = open("CONARY").readlines()
    rev = config[2].strip().rsplit(":", 1)[1]
    return rev

def locate_rev_in_log(revisions, rev):
    for i in range(len(revisions)):
        if revisions[i][0] == rev:
            return i
    return None

def do_pull():
    current_rev = read_local_version()
    print "local revision:", current_rev
    s = getstatusoutput("cvc update")
    if s[0] != 0:
        print "error with cvc update:", s[1]
        sys.exit()

    remote_rev = read_local_version()
    print "remote revision:", remote_rev

    if current_rev == remote_rev:
        print "no changes found"
        return

    revisions = parse_history()
    ix = locate_rev_in_log(revisions, current_rev)
    commit_to_git(revisions[:ix])
    print "done"
