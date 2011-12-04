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

def check_output(*args, **kw):
    '''
    Like the check_output function in the subprocess module of a recent
    Python, but backported to 2.6.
    '''

    p = subprocess.Popen(*args, stdout = subprocess.PIPE, **kw)
    output = p.communicate()[0]
    retcode = p.poll()
    if retcode != 0:
        raise subprocess.CalledProcessError(retcode, args[0])
    return output

def is_commit_header(line):
    '''Check if a line is the header of a commit

    For every line in cvc log output (except the first two lines), if not
    starting with a whitespace, it's a "commit header.

    E.g.

        tip-1 Og Maciel (omaciel@foresightlinux.org) Fri Jan 29 12:41:57 2010
            Version bump and now pulling from bitbucket.

    '''
    return (len(line) > 0) and not line[0].isspace()

def parse_commit_header(line):
    '''Parse commit information from a commit header
    '''
    s = line.split()
    rev = s[0]
    who = " ".join(s[1:-5])
    date = " ".join(s[-5:])

    return rev, who, date

def reformat_msg_body(lines):
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
        revision, author, date = parse_commit_header(log[0])
        msg = reformat_msg_body(log[1:])

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

def locate_next_commit(history, begin):
    '''Locate the next block of commit message in history

    history is the 'cvc log' output
    '''
    nxt = begin
    while nxt < len(history):
        if is_commit_header(history[nxt]):
            break
        else:
            nxt += 1
    return nxt

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
        print "I haven't touched the git repo yet, so it's probably left fine."
        print "But if any doubt, please have a check."
        sys.exit(1)

    pkg = history[0].split()[-1].split(":")[0]
    branch = history[1].split()[-1]
    history = history[2:] # drop the first two lines

    i = locate_next_commit(history, 0)

    resume_point = resume_info.get(pkg, None)
    # Note that in 'cvc log' newer revisions come first
    got_resume_point = False

    while i < len(history):
        n = locate_next_commit(history, i+1)
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

def parse_logs(pkgs, cachedir, resume_info):
    '''Parse the commit history of pkgs

    The "cvc log" output for all packages should already be cached in cachedir.

    Resume_info should contain the last revision of packages that have been
    converted, so we can only convert revisions newer than that.

    resume_info is an in/out parameter; it will be updated with
    information of this run. It must be a dict, even if empty.

    Return a list of CvcCommit, sorted by commit date
    '''

    commits = []
    assert isinstance(resume_info, dict)

    for pkg in pkgs:
        pkg = pkg.split(":")[0] # accept package names with :source or not
        f = open("%s/%s.log" % (cachedir, pkg))
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

def init_git_repo(gitdir):
    subprocess.check_call(["git", "init"], stdout=open(os.devnull, "w"),
            cwd=gitdir)

def get_git_branch(gitdir):
    # Use `git status` instead of `git branch` since it can handle initial commit
    output = check_output(["git", "status"], cwd=gitdir,
            stderr=subprocess.STDOUT)
    branch = output.splitlines()[0].split()[-1]
    return branch

def is_initial_repo(gitdir):
    status = check_output(["git", "status"], cwd=gitdir,
            stderr=subprocess.STDOUT)
    status = status.splitlines()
    if len(status) > 2 and status[2] == "# Initial commit":
        return True
    else:
        return False

def get_git_head(gitdir):
    if is_initial_repo(gitdir):
        head = "Initial commit"
    else:
        output = check_output(
                ["git", "log", "-1", "--format=oneline", "--abbrev-commit"],
                cwd=gitdir, stderr=subprocess.STDOUT)
        head = output.strip()
    return head

def get_resume_info(gitdir):
    '''Read the converted revisions out of a git note
    '''
    if is_initial_repo(gitdir):
        ret = {}
    else:
        output = check_output(["git", "notes", "show"], cwd=gitdir,
                stderr=subprocess.STDOUT)
        ret = dict([x.split("=") for x in output.split()])
    return ret

def store_progress(resume_info, gitdir):
    '''Store the last revision of each converted package in a git note
    '''
    msg = " ".join(["%s=%s" % (k, v) for (k, v) in resume_info.items()])
    subprocess.check_call(["git", "notes", "add", "-m", msg],
            stdout=open(os.devnull, "w"), cwd=gitdir)

def read_package_list(sourcelistfile):
    f = open(sourcelistfile)
    sources = f.readlines()
    f.close()
    ret = [ln.split(":", 0)[0] for ln in sources]
    return ret

def add_options():
    usage = ("Usage: %prog --label=CONARY_LABEL --cachedir=DIR --git-dir=DIR [options]\n"
             "       %prog --label=CONARY_LABEL --cachedir=DIR --git-dir=DIR [options] <pkg-name> [<more-packages>]")
    desc = ("Take the data collected by get-all-pkg-log and create a git repo. "
            "If a list of packages are specified, will convert these packages only.")

    parser = optparse.OptionParser(usage=usage, description=desc)
    parser.add_option("--label", dest="label",
            help="Which label to convert? (Required)")
    parser.add_option("--cachedir", dest="cachedir",
            help="Need a cache dir to put intermediate stuff. This dir will " \
                 "be reused when you run cvc2git again in the future, so it " \
                 "better not resides in a regularly cleaned-up /tmp, e.g. "\
                 "(Required)")
    parser.add_option("--git-dir", dest="gitdir",
            help="Where should I create the git repo? (Required)")
    parser.add_option("--no-refresh", dest="norefreshcache",
            help="If specified, will not refresh the cache at cachedir",
            action="store_true")

    options, args = parser.parse_args()
    if not (options.label and options.cachedir and options.gitdir):
        parser.print_help()
        sys.exit(1)
    return options, args

def create_git_repo(gitdir):
    if not os.path.exists(gitdir):
        os.makedirs(gitdir)
    if not os.path.exists(gitdir + "/.git"):
        init_git_repo(gitdir)
        print "New git repo created at %s." % gitdir
    else:
        branch = get_git_branch(gitdir)
        head = get_git_head(gitdir)
        print "Reusing the git repo at %s (branch: %s; HEAD: `%s`)." % (
                gitdir, branch, head)

def main():
    options, args = add_options()

    cachedir = os.path.abspath(options.cachedir)
    gitdir = os.path.abspath(options.gitdir)
    pkgs = args

    if not options.norefreshcache:
        prefix = os.path.dirname(sys.argv[0])
        subprocess.check_call([prefix + "/get-all-pkg-log",
            options.label, cachedir])

    if not pkgs:
        pkgs = read_package_list(cachedir + "/sources-list")
    if not pkgs:
        print "Got nothing to convert. Aborting."
        sys.exit(1)
    print "%d packages to be converting" % len(pkgs)

    create_git_repo(gitdir)

    resume_info = get_resume_info(gitdir)
    commits = parse_logs(pkgs, cachedir + "/logs", resume_info)
    if commits:
        apply_commits(commits, gitdir)
        store_progress(resume_info, gitdir)
        head = get_git_head(gitdir)
        print "Conversion succeeded. HEAD of the git repo is now: `%s`" % head
    else:
        print "The git repo is already up to date."

if __name__ == "__main__":
    main()
