#!/usr/bin/env python

# Take a list of :source package names, read their commit history (from a cache
# dir), parse it into python, sort by commit date, and convert into git

from datetime import datetime
import re
import optparse
import os
import os.path
import shutil
import subprocess
import sys

def _is_commit_header(line):
    '''Check if a line is the header of a commit

    For every line in cvc log output (except the first two lines), if not
    starting with a whitespace, it's a "commit header.

    E.g.

        tip-1 Og Maciel (omaciel@foresightlinux.org) Fri Jan 29 12:41:57 2010
            Version bump and now pulling from bitbucket.

    '''
    return (len(line) > 0) and not line[0].isspace()

def _parse_commit_header(line):
    '''Parse commit information from a commit header
    '''
    s = line.split()
    rev = s[0]
    who = " ".join(s[1:-5])
    date = " ".join(s[-5:])

    return rev, who, date

def _reformat_msg_body(lines):
    '''Strip leading/ending blanks in the commit message

    lines is a list containing all lines of the original message.
    Return a string containing the whole message reformated.
    '''
    ret = "\n".join([x.strip() for x in lines])
    return ret.rstrip() # removing extra empty lines

class CvcCommit:
    '''Turns a snippet of commit log into python object
    '''
    def __init__(self, pkg, branch, log):
        '''log should be a complete log snippet for one commit, typically:

            0.86-0.1 jdoe (john.doe@gmail.com) Mon Aug 30 16:07:12 2010
                version bump

                More details here.

        '''
        self.pkg = pkg
        self.branch = branch

        self.revision = None
        # author name
        self.authorn = None
        # author email
        self.authore = None
        self.date = None
        self.msg = None

        self._parse(log)

    def _parse(self, log):
        revision, author, date = _parse_commit_header(log[0])
        msg = _reformat_msg_body(log[1:])

        self.revision = revision
        self.authorn, self.authore = re.match("^(.*) \((.*)\)$", author).groups()
        self.date = datetime.strptime(date, "%a %b %d %H:%M:%S %Y")
        self.msg = msg

    def expand(self):
        return [self.pkg, self.branch, self.revision, self.authorn,
                self.authore, self.date, self.msg]

    def __str__(self):
        return ("pkg: %s\nbranch: %s\n"
                "revision: %s\nauthor: %s<%s>\ndate: %s\nmsg: %s\n" %
                    self.expand())

def _locate_next_commit(history, begin):
    '''Locate the next block of commit message in history

    history is the 'cvc log' output
    '''
    next = begin
    while next < len(history):
        if _is_commit_header(history[next]):
            break
        else:
            next += 1
    return next

def get_commits(history, resume_info):
    '''Extract all commits from one package's "cvc log"

    history is a list of lines containing the whole 'cvc log' output

    E.g.

        Name  : epdb:source
        Branch: /foresight.rpath.org@fl:2-devel

        tip-1 Og Maciel (omaciel@foresightlinux.org) Fri Jan 29 12:41:57 2010
            Version bump and now pulling from bitbucket.
    '''
    commits = []

    # the first two lines must be Name: and Branch:
    if not (history[0].startswith("Name") and history[1].startswith("Branch")):
        print "Error! %s seems mal-formated. Aborting."
        print "I haven't touched the git repo yet, so it's probably ok."
        print "But if any doubt, please have a check."
        sys.exit(1)

    pkg = history[0].split()[-1].split(":")[0]
    branch = history[1].split()[-1]
    history = history[2:] # drop the first two lines

    i = _locate_next_commit(history, 0)

    resume_point = resume_info.get(pkg, None)
    # Note that in 'cvc log' newer revisions come first
    got_resume_point = False

    while i < len(history):
        n = _locate_next_commit(history, i+1)
        commit = CvcCommit(pkg, branch, history[i:n])
        if not got_resume_point and commit.revision == resume_point:
            got_resume_point = True
        if not got_resume_point:
            commits.append(commit)
        i = n

    # If we are refreshing and there is no new revisions, commits can be empty
    if commits:
        resume_info[pkg] = commits[0].revision
    return commits

def sort_commits(commits):
    '''sort the list of CvcCommit according to commit date

    Sort commits in place.
    '''
    commits.sort(key=lambda c: c.date)

def parse_logs(pkgs, logsdir, resume_info={}):
    '''Parse the commit history of pkgs

    The "cvc log" output for all packages should already be cached in logsdir.

    Resume_info should contain the last revision of packages that have been
    converted, so we can only convert revisions newer than that.

    resume_info is an in/out parameter; it will be updated with
    information of this run.

    Return a list of CvcCommit, sorted by commit date
    '''

    commits = []

    for pkg in pkgs:
        pkg = pkg.split(":")[0] # accept package names with :source or not
        f = open("%s/%s.log" % (logsdir, pkg))
        history = f.read().strip().splitlines()
        commits.extend(get_commits(history, resume_info))
        f.close()

    sort_commits(commits)
    return commits

def apply_commits(commits, gitdir):
    saved_cwd = os.getcwd()
    os.chdir(gitdir)

    devnull = open(os.devnull, "w")

    count = len(commits)
    for i, commit in enumerate(commits):
        pkg, branch, revision, authorn, authore, dater, msg = commit.expand()
        date = dater.strftime("%a %b %d %H:%M:%S %Y +0000")

        d = dater.strftime("%Y-%m-%d")
        percent = (i + 1) * 100 / count
        clear_line = "\33[2K\r"
        sys.stdout.write("%sconverting [%d/%d %d%%] %s %s=%s..." %
                (clear_line, i+1, count, percent, d, pkg, revision))
        sys.stdout.flush()

        if os.path.exists(pkg):
            shutil.rmtree(pkg)
        subprocess.check_call(["cvc", "checkout",
                               "%s=%s/%s" % (pkg, branch, revision)],
                              stdout=devnull)
        # remove the CONARY file. We don't want it in the repo
        os.remove("%s/CONARY" % pkg)

        subprocess.check_call(["git", "add", "--all", pkg])
        subprocess.check_call(
                ["git", "commit", "--message", msg,
                    "--allow-empty",
                    "--allow-empty-message"],
                stdout=devnull,
                env={"GIT_AUTHOR_NAME": authorn,
                     "GIT_AUTHOR_EMAIL": "<%s>" % authore,
                     "GIT_AUTHOR_DATE": date,
                     "GIT_COMMITTER_NAME": authorn,
                     "GIT_COMMITTER_EMAIL": "<%s>" % authore,
                     "GIT_COMMITTER_DATE": date})
    devnull.close()
    print
    os.chdir(saved_cwd)

def assert_dir_exist(d, want_exist):
    exist = os.path.exists(d)
    if want_exist and not exist:
        print "Error: %s doesn't exist." % d
        sys.exit(1)
    elif not want_exist and exist:
        print "Error: %s already exists." % d
        sys.exit(1)

def init_git_repo(gitdir):
    os.mkdir(gitdir)
    subprocess.check_call(["git", "init"], stdout=open(os.devnull, "w"),
            cwd=gitdir)

def get_git_branch(gitdir):
    # Use `git status` instead of `git branch` since it can handle initial commit
    output = subprocess.Popen(["git", "status"], cwd=gitdir,
            stdout=subprocess.PIPE).communicate()[0]
    branch = output.splitlines()[0].split()[-1]
    return branch

def is_initial_repo(gitdir):
    status = subprocess.Popen(["git", "status"], cwd=gitdir,
            stdout=subprocess.PIPE).communicate()[0]
    status = status.splitlines()
    if len(status) > 2 and status[2] == "# Initial commit":
        return True
    else:
        return False

def get_git_head(gitdir):
    if is_initial_repo(gitdir):
        head = "Initial commit"
    else:
        output = subprocess.Popen(["git", "log", "-1", "--format=oneline", "--abbrev-commit"],
                stdout=subprocess.PIPE, cwd=gitdir).communicate()[0]
        head = output.strip()
    return head

def get_resume_info(gitdir):
    '''Read the converted revisions out of a git note
    '''
    if is_initial_repo(gitdir):
        ret = {}
    else:
        output = subprocess.Popen(["git", "notes", "show"], cwd=gitdir,
                stdout=subprocess.PIPE).communicate()[0]
        ret = dict([x.split("=") for x in output.split()])
    return ret

def store_progress(resume_info, gitdir):
    '''Store the last revision of each converted package in a git note
    '''
    msg = " ".join(["%s=%s" % (k, v) for (k, v) in resume_info.items()])
    subprocess.check_call(["git", "notes", "add", "-m", msg],
            stdout=open(os.devnull, "w"), cwd=gitdir)

def add_options():
    usage = "Usage: %prog --history-dir=DIR --git-dir=DIR <pkg-name> [<more-packages>]"
    desc = ("Take a list of package names, create a git repo according"
            " to their 'cvc log'. Need a list of package names, whose 'cvc log'"
            " output should be available in <history-dir>")

    parser = optparse.OptionParser(usage=usage, description=desc)
    parser.add_option("--history-dir", dest="historydir",
            help="Where can I get the 'cvc log' outputs? (Required)")
    parser.add_option("--git-dir", dest="gitdir",
            help="Where should I create the git repo? It shouldn't already exist. If it is, specify --no-init. (Required)")
    parser.add_option("--no-init-git", dest="noinitgit", action="store_true",
            help="If specified, assume there is an existing git repo at git-dir. Or else I will create the dir and repo.")
    parser.add_option("--refresh", dest="refresh", action="store_true",
            help="If specified, update the git repo to the state specified in history-dir/sources.list. Implies --no-init-git. Info of last run must still be available on a git note on HEAD.")

    options, args = parser.parse_args()
    if not options.historydir:
        parser.error("Need a --history-dir")
    if not options.gitdir:
        parser.error("Need a --git-dir")
    if not args:
        parser.error("What do you want me to convert?")
    return options, args

def main():
    options, args = add_options()

    logsdir = os.path.abspath(options.historydir)
    gitdir = os.path.abspath(options.gitdir)
    pkgs = args

    initgit = True
    refresh = options.refresh
    if options.noinitgit or refresh:
        initgit = False

    if initgit:
        assert_dir_exist(gitdir, False)
        init_git_repo(gitdir)
        print "New git repo created at %s." % gitdir
    else:
        assert_dir_exist(gitdir, True)
        branch = get_git_branch(gitdir)
        head = get_git_head(gitdir)
        print "Will reuse the git repo at %s (branch: %s; HEAD: `%s`)." % (gitdir, branch, head)

    resume_info = {}
    if refresh:
        resume_info = get_resume_info(gitdir)

    commits = parse_logs(pkgs, logsdir, resume_info)
    if commits:
        apply_commits(commits, gitdir)
        store_progress(resume_info, gitdir)
        head = get_git_head(gitdir)
        print "Conversion succeeded. HEAD of the git repo is now: `%s`" % head
    else:
        print "Nothing changed."

if __name__ == "__main__":
    main()
