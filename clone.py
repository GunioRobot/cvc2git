#!/usr/bin/python

from commands import getoutput, getstatusoutput
import os
import sys

def start_with_version(line):
    return (len(line) > 0) and line[0].isdigit()

def find_next_commit(buffer, begin):
    next = begin
    while next < len(buffer):
        if start_with_version(buffer[next]):
            break
        else:
            next += 1
    return next

def parse_commit(line):
    s = line.split()
    rev = s[0]
    who = ' '.join(s[1:-5])
    date = '%s, %s %s %s %s +0000' % (s[-5], s[-3], s[-4], s[-1], s[-2])
    #0,3,1,5,4
    return rev, who, date

def format_commit_msg(msgs):
    ret = '\n'.join([x.strip() for x in msgs])
    return ret.rstrip()

def parse_history():
    revisions = []
    history = getoutput("cvc log").splitlines()

    # drop the first several lines
    i = find_next_commit(history, 0)

    while i < len(history):
        revision, committer, date = parse_commit(history[i])
        t = find_next_commit(history, i+1)
        message = format_commit_msg(history[i+1:t])
        i = t
        revisions.append((revision, committer, date, message))

    return revisions

def checkout(trove, dest):
    print "checking out %s" % trove, ("to " + dest) if dest else ""
    extra = ("--dir=" + dest) if dest else ""
    s = getstatusoutput("cvc checkout %s %s" % (trove, extra))
    if s[0] == 0:
        # TODO handle clone dummy-test:source=/jesse.rpath.org@fl:2-devel
        dir = dest if dest else trove.split("=")[0]
        return os.path.abspath(dir)
    print "cvc co fails:", s[1]
    return None

def get_file_list():
    '''recognize the files in <package>:source'''
    ls_result = getoutput("ls | /bin/grep -v CONARY").split()
    conary_config = open("CONARY").read()
    return [x for x in ls_result if x in conary_config]

def commit_to_git(revisions):
    print "converting to git..."
    getstatusoutput("git init")
    for (revision, committer, date, message) in revisions[::-1]:
        author = committer.replace("(", "<", 1).replace(")", ">", 1)
        msg = "%s\n\ncvc revision: %s" % (message, revision)
        s = getstatusoutput("cvc update %s" % revision)
        if s[0] != 0:
            print "error with cvc update:", s[1]
        files = get_file_list()
        s = getstatusoutput("git add %s" % " ".join(files))
        if s[0] != 0:
            print "error with git commit:", s[1]
        s = getstatusoutput("git commit --all --author='%s' --date='%s' --message='%s'"
                % (author, date, msg))
        if s[0] != 0:
            print "error with git commit:", s[1]

def do_clone(trove, dest=None):
    workdir = checkout(trove, dest)
    if not workdir:
        sys.exit()

    # change to work directory
    os.chdir(workdir)
    revisions = parse_history()

    commit_to_git(revisions)
    print "done"

#######################################

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
