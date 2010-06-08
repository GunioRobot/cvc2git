from commands import getoutput, getstatusoutput
import sys
import subprocess

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

    return rev, who, date

def format_commit_msg(msgs):
    ret = '\n'.join([x.strip() for x in msgs])
    return ret.rstrip()

def parse_history():
    '''Revisions are returned with newest first'''
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

def get_file_list():
    '''recognize the files in <package>:source'''
    ls_result = getoutput("ls | /bin/grep -v CONARY").splitlines()
    conary_config = open("CONARY").read()
    return [x for x in ls_result if x in conary_config]

def commit_to_git(revisions):
    rev_count = len(revisions)
    getstatusoutput("git init")
    for (i, (revision, committer, date, message)) in enumerate(revisions[::-1]):
        sys.stdout.write("converting [%d/%d] commits to git...  revision=%s\r"
                % (i+1, rev_count, revision))
        sys.stdout.flush()

        author = committer.replace("(", "<", 1).replace(")", ">", 1)
        msg = "%s\n\ncvc revision: %s" % (message, revision)
        s = getstatusoutput("cvc update %s" % revision)
        if s[0] != 0:
            print "error with cvc update:", s[1]
        files = get_file_list()
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

def create_ignore_file():
    '''ignore CONARY'''
    open(".gitignore", "w").write("CONARY\n")
