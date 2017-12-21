# BuildBot Changehook for Sourceforge and Allura

This package implements a changehook so that [BuildBot](https://buildbot.net/)
can be used with projects on [Sourceforge](https://sourceforge.net/) or its
open-source cousin, [Allura](https://allura.apache.org/).

Specifically, it enables you to point [webhooks](https://forge-allura.apache.org/p/allura/wiki/Webhooks/)
at buildbot so that it can build the requested changes.

### Shortcomings

At present, the messages sent from Allura to buildbot don't contain enough
information to accurately determine the scope of changes being reported.  I
have an [open ticket](https://forge-allura.apache.org/p/allura/tickets/8151/)
on this, and more information can be found there.

There is another bug, unreported at the moment, that changes are stamped
with their *push* time, not the *commit* time.  Combined with what might be
a separate issue, that batches of pushes show up in reverse order, this
sometimes results in buildbot building against the wrong latest version when
multiple changes are pushed.  The workaround is to schedule other builds at
regular intervals (perhaps once a day) to pick up wrongly-ordered changes.

## Installation

On BuildBot v0.9.10 and later, simply clone this repository and install this
package in the buildbot master's environment:

```sh
git clone https://github.com/jjjordan/buildbot-allura-changehook.git
cd buildbot-allura-changehook
python setup.py install
```

On earlier versions of BuildBot, copy `allura.py` into the `hooks`
directory.  For example, in the Buildbot Docker container, this would look
like:

```sh
git clone https://github.com/jjjordan/buildbot-allura-changehook.git
cd buildbot-allura-changehook
cp buildbot_allura_changehook/allura.py /usr/lib/python2.7/site-packages/buildbot/www/hooks
```

## Usage

To use this changehook, add an entry to your `master.cfg`:

```python
c['www'] = {
	# ...Other stuff...
	'change_hook_dialects': {
		'allura': {
			'strict': True,
			'secret': '<shared secret here>',
			'repository_kind': 'hg',
		}
	}
}
```

### Options

There are no required options (although **strict** and **secret** must be
specified together.  The supported options are:

**strict** - Verify the incoming signature from Allura. If this is provided,
then **secret** must also be provided.

**secret** - Shared secret with Allura.  Allura will tell you what the
secret is when you register your change hook.

**repository_kind** - There is not enough information in the incoming
request to distinguish between git and Mercurial (svn can be detected), so
it must be specified here.  This can be one of `svn`, `hg`, or `git`.

**codebase** - This is either a function that accepts the JSON-parsed
payload and returns a codebase identifier, or a codebase identifier itself. 
See the [Buildbot documentation on codebases](http://docs.buildbot.net/latest/manual/concepts.html#codebase)
for more information.  If you only have a single repository, you can ignore
this option.

**repository** - The address of the source code repository.  Sourceforge
repositories can (usually) be detected from the incoming data and this
should not be specified.  If you have trouble with sourceforge, or are using
Allura, you should specify this option.

## Webhook location

Point Allura at your changehook, which will be found at: `http://*host*/*base path*/change_hook/allura`

## About

I have no affiliation with either buildbot, Sourceforge, Apache Allura, etc. 
I work on a small project hosted on sourceforge and needed this to plug one
thing into another.  Support will be made on a best-effort basis.  Tinkering
is encouraged, pull requests are better.  I hope this helps somebody.

This project is MIT-licensed.
