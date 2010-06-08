from commands import getstatusoutput
import sys

from utils import (
        commit_to_git,
        create_ignore_file,
        locate_rev_in_log,
        parse_history,
        read_local_version,
        )

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

def in_place_convert():
    # check if is cvc package dir
    create_ignore_file()

    revisions = parse_history()
    current_rev = read_local_version()
    ix = locate_rev_in_log(revisions, current_rev)

    commit_to_git(revisions[ix:])
