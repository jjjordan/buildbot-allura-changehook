
# Hacked together by John J. Jordan <jj@jjjordan.io>
# License: MIT

# This is documented here: https://forge-allura.apache.org/p/allura/wiki/Webhooks/

import hashlib
import hmac
import logging
import re

from dateutil.parser import parse as dateparse
from twisted.python import log

from buildbot.util import bytes2NativeString, unicode2bytes

try:
    import json
    assert json
except ImportError:
    import simplejson as json

_HEADER_SIG = 'X-Allura-Signature'

# repository.name field values
_REPO_NAME_SVN = 'SVN'
_REPO_NAME_HG = 'Mercurial'
_REPO_NAME_GIT = 'Git'
_REPO_SVN = 'svn'
_REPO_HG = 'hg'
_REPO_GIT = 'git'

# Map the above into strings that buildbot likes
_REPO_KINDS = {
    _REPO_NAME_SVN: _REPO_SVN,
    _REPO_NAME_HG: _REPO_HG,
    _REPO_NAME_GIT: _REPO_GIT,
}

class AlluraEventHandler(object):
    def __init__(self, master, options):
        options = options or {}
        self.master = master
        self.options = options
        
        self._secret = options.get('secret', None)
        self._strict = options.get('strict', False)
        self._codebase = options.get('codebase', None)
        self._repository = options.get('repository', None)
        self._repokind = options.get('repository_kind', None)
        
        if self._strict and not self._secret:
            raise ValueError("Strict mode is requested while no secret is provided")

    def getChanges(self, request):
        payload = self._get_payload(request)

        # There is only one request type here: push
        # ...and this is basically a simplified Github webhook.

        repo_kind = self._get_repokind(payload)

        if repo_kind == _REPO_GIT:
            # Only care about regular heads or tags
            if not re.match(r"^refs/(heads|tags)/(.+)$", payload['ref']):
                return [], 'git'
        elif repo_kind == _REPO_HG:
            # Commits will generally fire two webhooks: one for the branch
            # that this went into, and one for 'tip'.  We'll ignore latter.
            if payload['ref'] == 'refs/tags/tip':
                return [], 'hg'

        changes = list(map(lambda commit: self.processCommit(payload, commit, repo_kind), payload['commits']))
        return changes, repo_kind

    def processCommit(self, payload, commit, repo_kind):
        files = []
        for kind in ('added', 'copied', 'removed', 'modified'):
            files.extend(commit.get(kind, []))

        change = {
            'files': files,
            'author': '{} <{}>'.format(commit['author']['name'], commit['author']['email']),
            'when_timestamp': dateparse(commit['timestamp']),
            'revision': commit['id'],
            'comments': commit['message'],
            'repository': self._get_repository(payload),
            'revlink': commit['url'],
            'project': payload['repository']['url'],
            'category': 'push',
        }

        if repo_kind == _REPO_GIT or repo_kind == _REPO_HG:
            ref = payload['ref']
            if ref.startswith("refs/heads"):
                change['branch'] = ref.split('/')[-1]
        elif repo_kind == _REPO_SVN:
            pass

        if callable(self._codebase):
            change['codebase'] = self._codebase(payload)
        elif self._codebase is not None:
            change['codebase'] = self._codebase

        return change

    def _get_payload(self, request):
        content = request.content.read()
        content = bytes2NativeString(content)

        signature = request.getHeader(_HEADER_SIG)
        signature = bytes2NativeString(signature)
        
        if not signature and self._strict:
            raise ValueError("Request has no required signature")

        if self._secret and signature:
            if not _verify(content, signature, unicode2bytes(self._secret)):
                raise ValueError("Hash mismatch")

        payload = json.loads(content)
        log.msg("Payload: {}".format(payload), logLevel=logging.DEBUG)

        return payload
    
    def _get_repository(self, payload):
        if self._repository is not None:
            # Due to the reason below, the user might want to supply
            # their own repository URL.  Sourceforge we can handle,
            # but if you're on some other deployment of Allura, all
            # bets are off...
            return self._repository
        
        repo = payload['repository']
        repo_url = repo['url']
        if 'sourceforge.net' in repo_url or 'sf.net' in repo_url:
            # This gives us a bogus repo URL -- the one that a user
            # would navigate to rather than the one you should point
            # a SCC client at.  Fortunately, the transformation is not
            # difficult.
            repo_kind = self._get_repokind(payload)
            if repo_kind == _REPO_HG:
                return "http://hg.code.sf.net" + repo['full_name']
            elif repo_kind == _REPO_GIT:
                return "http://git.code.sf.net" + repo['full_name']
            elif repo_kind == _REPO_SVN:
                return "http://svn.code.sf.net" + repo['full_name']
            else:
                raise ValueError("Couldn't determine sourceforge repository URL: consider supplying repository argument")
        
        raise ValueError("Couldn't determine allura repository URL: consider supplying repository argument")
    
    def _get_repokind(self, payload):
        if self._repokind is not None:
            return self._repokind
        
        # Try to guess by the name
        repo_name = payload['repository']['name']
        if repo_name in _REPO_KINDS:
            return _REPO_KINDS[repo_name]
        
        # Well... we can identify SVN by its commit format.
        for c in payload['commits']:
            if c['id'].startswith('r'):
                return _REPO_SVN
        
        # Yeah, we can't figure out the repository kind from the hook.
        # We probably *can* go to the API, but I don't know how that would interact
        # with twisted.
        raise ValueError("Couldn't determine repository kind from request")

# This is (almost) straight from allura documentation (see link at top)
def _verify(payload, signature, secret):
    actual_signature = hmac.new(secret, payload, hashlib.sha1)
    actual_signature = 'sha1=' + actual_signature.hexdigest()
    return hmac.compare_digest(actual_signature, signature)

# Old-style entrypoint
def getChanges(options, request):
    return AlluraEventHandler(None, options).getChanges(request)
