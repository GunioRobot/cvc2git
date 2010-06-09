from commands import getoutput, getstatusoutput
import sys
import os.path
import subprocess

def _is_commit_header(line):
    '''Check if a line is the header of a commit

    For every line in cvc log output, if starting with a number, it's a "commit
    header"

    '''
    return (len(line) > 0) and line[0].isdigit()

def _locate_next_commit(buffer, begin):
    '''Locate the next block of commit information in buffer

    buffer should be a fragment from cvc log output
    '''
    next = begin
    while next < len(buffer):
        if _is_commit_header(buffer[next]):
            break
        else:
            next += 1
    return next

def _parse_commit_header(line):
    '''Parse commit information from a commit header
    '''
    s = line.split()
    rev = s[0]
    who = ' '.join(s[1:-5])
    date = '%s, %s %s %s %s +0000' % (s[-5], s[-3], s[-4], s[-1], s[-2])

    return rev, who, date

def _reformat_msg_body(msgs):
    '''Strip leading/ending blanks in the commit message

    msgs is a list containing all lines of the original message.
    Return a string containing the whole reformated message.
    '''
    ret = '\n'.join([x.strip() for x in msgs])
    return ret.rstrip() # removing extra empty lines

def parse_history():
    '''Revisions are returned with newest first'''
    revisions = []
    history = getoutput("cvc log").splitlines()

    # drop the first several lines
    i = _locate_next_commit(history, 0)

    while i < len(history):
        revision, committer, date = _parse_commit_header(history[i])
        t = _locate_next_commit(history, i+1)
        message = _reformat_msg_body(history[i+1:t])
        i = t
        revisions.append((revision, committer, date, message))

    return revisions

def _get_file_list():
    '''Make a list of the files in the package

    Collect all files that appear in CONARY and also exist in current dir.
    '''
    ls_result = getoutput("ls | /bin/grep -v CONARY").splitlines()
    conary_config = open("CONARY").read()
    return [x for x in ls_result if x in conary_config]

def commit_to_git(revisions):
    rev_count = len(revisions)
    for (i, (revision, committer, date, message)) in enumerate(revisions[::-1]):
        sys.stdout.write("converting [%d/%d] commits to git...  revision=%s\r"
                % (i+1, rev_count, revision))
        sys.stdout.flush()

        author = committer.replace("(", "<", 1).replace(")", ">", 1)
        msg = "%s\n\ncvc revision: %s" % (message, revision)
        s = getstatusoutput("cvc update %s" % revision)
        if s[0] != 0:
            print "error with cvc update:", s[1]
        files = _get_file_list()
        s = subprocess.call(["git", "add"] + files,
                stdout=open('/dev/null', 'w'))
        if s != 0:
            print "error with git add, exiting"
        s = subprocess.call(["git", "commit",
            "--all",
            "--author", author,
            "--date", date,
            "--message", msg],
            stdout=open('/dev/null', 'w'))
        if s != 0:
            print "error with git commit, exiting"
            sys.exit()
    print # needed, or the 'converting...' line will be overwritten

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

def init_git_repository():
    if os.path.exists(".gitignore"):
        print "Warning: .gitignore already exists. Skip creating .gitignore."
    else:
        open(".gitignore", "w").write("CONARY\n")

    if os.path.exists(".git"):
        print "Error: can't initialize git repository. .git already exists."
        return False
    else:
        getstatusoutput("git init")
        return True

def is_cvc2git_repo_dir():
    '''Check if current directory is a repository created by cvc2git
    '''
    return os.path.isfile("CONARY") and os.path.isdir(".git")

def is_conary_package_dir():
    '''Check if current directory contains a conary source package
    '''
    return os.path.isfile("CONARY")
