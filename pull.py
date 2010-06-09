from commands import getstatusoutput
import sys

from utils import (
        commit_to_git,
        init_git_repository,
        is_conary_package_dir,
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
    if not is_conary_package_dir():
        print "Error: current directoy must contain a conary source package, as created by cvc checkout"
        return

    if not init_git_repository():
        return

    revisions = parse_history()
    current_rev = read_local_version()
    ix = locate_rev_in_log(revisions, current_rev)

    commit_to_git(revisions[ix:])
