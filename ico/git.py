from git import Repo
import os
import time

join = os.path.join
repo = Repo(os.getcwd())
assert not repo.bare

repo.config_reader()

def git_sanitycheck():
    git_ismaster()
    git_isold()
    git_isdirty()

def git_isdirty():
    if repo.is_dirty():
        raise RuntimeError("The repository is not committed, won't continue. Please commit.")

    return

def git_ismaster():
    # User can override git_isold checking for a week
    if ((float(os.getenv("ICO_DEPLOY_ANYWAY", 0)) + 604800) > time.time()):
        return True

    if (repo.active_branch.commit != repo.heads.master.commit):
        raise RuntimeError("This branch is not 'master'. Please switch to master, or use the following command to postpone this check for a week:\nexport ICO_DEPLOY_ANYWAY=" + str(time.time()))

def git_isold():
    git_root = repo.git.rev_parse("--show-toplevel")
    latest_pull = os.stat(git_root + "/.git/FETCH_HEAD").st_mtime
    deadline = latest_pull + 604800 # One week from latest commit

    if (time.time() > deadline):
        raise RuntimeError("You haven't pulled for a week. Please do git pull.")
    else:
        return

def git_current_commit():
    return repo.active_branch.commit
