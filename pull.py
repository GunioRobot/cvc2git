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

    revisions = parse_history()
    ix = locate_rev_in_log(revisions, current_rev)
    if not ix:
        print "no changes found"
        return
    commit_to_git(revisions[:ix])
    print "done"

def convert_in_place():
    # check if is cvc package dir
    create_ignore_file()

    revisions = parse_history()
    current_rev = read_local_version()
    ix = locate_rev_in_log(revisions, current_rev)

    commit_to_git(revisions[ix:])
