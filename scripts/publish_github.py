"""Publish this prepared project using the user's normal local GitHub login.

No password/token is accepted in arguments or saved by this script. Git handles
sign-in. An existing Git credential is used only in memory for the Pages API.
"""
import json, os, subprocess, time, urllib.error, urllib.request, webbrowser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO='abbas-asghari/Pharma-Analytics'
REMOTE='https://github.com/'+REPO+'.git'
PAGES='https://api.github.com/repos/'+REPO+'/pages'
SETTINGS='https://github.com/'+REPO+'/settings/pages'
GIT=os.environ.get('PHARMA_GIT','git')
if GIT=='git':
    import shutil
    if not shutil.which('git'):
        bundled=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'
        if bundled.exists():GIT=str(bundled)

def git(*args, capture=False):
    return subprocess.run([GIT,*args],cwd=ROOT,text=True,check=True,
                          stdout=subprocess.PIPE if capture else None)

def main():
    if not (ROOT/'.git').exists():
        git('init','-b','main')
        git('remote','add','origin',REMOTE)
    remote=git('remote','get-url','origin',capture=True).stdout.strip()
    if remote.rstrip('/').removesuffix('.git')!=REMOTE.removesuffix('.git'):
        raise RuntimeError('This folder points to a different repository. No changes were published.')
    branch=git('branch','--show-current',capture=True).stdout.strip()
    if branch!='main':raise RuntimeError('Expected the main branch. No branch was changed automatically.')
    git('add','--all')
    changes=subprocess.run([GIT,'diff','--cached','--quiet'],cwd=ROOT)
    if changes.returncode==1:
        git('-c','user.name=Codex','-c','user.email=codex@localhost','commit','-m',
            'Build interactive pharma analytics dashboard and reproducible data deliverables')
    elif changes.returncode!=0:raise RuntimeError('Could not inspect staged changes.')
    print('Publishing to '+REMOTE+'\nComplete the normal GitHub sign-in if Git opens it.',flush=True)
    git('push','-u','origin','main')  # never force-push
    print('Repository upload completed.',flush=True)
    credential=subprocess.run([GIT,'credential','fill'],input='protocol=https\nhost=github.com\n\n',
                              cwd=ROOT,capture_output=True,text=True,
                              env=os.environ|{'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'})
    fields=dict(line.split('=',1) for line in credential.stdout.splitlines() if '=' in line)
    token=fields.get('password')
    if credential.returncode or not token:
        print('Open Pages settings: select main and /docs, then Save.');webbrowser.open(SETTINGS);return
    def api(method='GET',payload=None):
        request=urllib.request.Request(PAGES,method=method,
            data=json.dumps(payload).encode() if payload else None,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                     'Content-Type':'application/json','User-Agent':'Pharma-Analytics-Publisher'})
        with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
    try:
        try: current=api()
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
            current=api('POST',{'source':{'branch':'main','path':'/docs'},'build_type':'legacy'})
        if current.get('source')!={'branch':'main','path':'/docs'}:
            current=api('PUT',{'source':{'branch':'main','path':'/docs'},'build_type':'legacy'})
        for _ in range(36):
            current=api();state=current.get('status');print('GitHub Pages: '+str(state),flush=True)
            if state=='built':
                url=current['html_url'];print('Dashboard: '+url,flush=True);webbrowser.open(url);return
            if state=='errored':raise RuntimeError('Pages build failed. Review the repository Actions tab.')
            time.sleep(5)
        print('Pages is configured and still building. Check the repository Actions tab.');webbrowser.open(SETTINGS)
    except urllib.error.HTTPError as e:
        print('Files are uploaded; Pages API returned HTTP '+str(e.code)+'. Select main and /docs in Pages settings.')
        webbrowser.open(SETTINGS)

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('Publication stopped: '+str(e))
        raise SystemExit(1)
