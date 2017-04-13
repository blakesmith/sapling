# (c) 2017-present Facebook Inc.
import collections
import marshal

from mercurial import (
    util,
)

class P4Exception(Exception):
    pass

def loaditer(f):
    "Yield the dictionary objects generated by p4"
    try:
        while True:
            d = marshal.load(f)
            if not d:
                break
            yield d
    except EOFError:
        pass

def revrange(start=None, end=None):
    """Returns a revrange to filter a Perforce path. If start and end are None
    we return an empty string as lookups without a revrange filter are much
    faster in Perforce"""
    revrange = ""
    if end is not None or start is not None:
        start = '0' if start is None else str(start)
        end = '#head' if end is None else str(end)
        revrange = "@%s,%s" % (start, end)
    return revrange

def parse_info():
    cmd = 'p4 -ztag -G info'
    stdout = util.popen(cmd, mode='rb')
    return marshal.load(stdout)

_config = None
def config(key):
    global _config
    if _config is None:
        _config = parse_info()
    return _config[key]

def parse_changes(client, startrev=None, endrev=None):
    "Read changes affecting the path"
    cmd = 'p4 --client %s -ztag -G changes -s submitted //%s/...%s' % (
        util.shellquote(client),
        util.shellquote(client),
        revrange(startrev, endrev))

    stdout = util.popen(cmd, mode='rb')
    for d in loaditer(stdout):
        c = d.get("change", None)
        oc = d.get("oldChange", None)
        if oc:
            yield P4Changelist(int(oc), int(c))
        elif c:
            yield P4Changelist(int(c), int(c))

def parse_filelist(client, startrev=None, endrev=None):
    if startrev is None:
        startrev = 0

    cmd = 'p4 --client %s -G files -a //%s/...%s' % (
            util.shellquote(client),
            util.shellquote(client),
            revrange(startrev, endrev))
    stdout = util.popen(cmd, mode='rb')
    for d in loaditer(stdout):
        c = d.get('depotFile', None)
        if c:
            yield d

def get_file(path, rev=None, clnum=None):
    """Returns a file from Perforce"""
    r = '#head'
    if rev:
        r = '#%d' % rev
    if clnum:
        r = '@%d' % clnum

    cmd = 'p4 print -q %s%s' % (util.shellquote(path), r)
    stdout = util.popen(cmd, mode='rb')
    content = stdout.read()
    return content

def parse_cl(clnum):
    """Returns a description of a change given by the clnum. CLnum can be an
    original CL before renaming"""
    cmd = 'p4 -ztag -G describe -O %d' % clnum
    stdout = util.popen(cmd, mode='rb')
    try:
        return marshal.load(stdout)
    except Exception:
        raise P4Exception(stdout)

def parse_usermap():
    cmd = 'p4 -G users'
    stdout = util.popen(cmd, mode='rb')
    try:
        for d in loaditer(stdout):
            if d.get('User'):
                yield d
    except Exception:
        raise P4Exception(stdout)

def parse_client(client):
    cmd = 'p4 -G client -o %s' % util.shellquote(client)
    stdout = util.popen(cmd, mode='rb')
    try:
        clientspec = marshal.load(stdout)
    except Exception:
        raise P4Exception(stdout)

    views = {}
    for client in clientspec:
        if client.startswith("View"):
            sview, cview = clientspec[client].split()
            # XXX: use a regex for this
            cview = cview.lstrip('/')  # remove leading // from the local path
            cview = cview[cview.find("/") + 1:] # remove the clientname part
            views[sview] = cview
    return views

def parse_fstat(clnum, filter=None):
    cmd = 'p4 -G fstat -e %d -T ' \
        '"depotFile,headAction,headType,headRev" "//..."' % clnum
    stdout = util.popen(cmd, mode='rb')
    try:
        for d in loaditer(stdout):
            if d.get('depotFile') and (filter is None or filter(d)):
                yield {
                    'depotFile': d['depotFile'],
                    'action': d['headAction'],
                    'type': d['headType'],
                    'rev': d['headRev'],
                }
    except Exception:
        raise P4Exception(stdout)

_filelogs = collections.defaultdict(dict)
def parse_filelogs(changelists, filelist):
    # we can probably optimize this by using fstat only in the case-inensitive
    # case and only for conflicts.
    global _filelogs
    for cl in changelists:
        fstats = parse_fstat(cl.cl, lambda f: f['depotFile'] in filelist)
        for fstat in fstats:
            _filelogs[fstat['depotFile']][cl.cl] = fstat
    for p4filename, filelog in _filelogs.iteritems():
        yield P4Filelog(p4filename, filelog)

class P4Filelog(object):
    def __init__(self, depotfile, data):
        self._data = data
        self._depotfile = depotfile

#    @property
#    def branchcl(self):
#        return self._parsed[1]
#
#    @property
#    def branchsource(self):
#        if self.branchcl:
#            return self.parsed[self.branchcl]['from']
#        return None
#
#    @property
#    def branchrev(self):
#        if self.branchcl:
#            return self.parsed[self.branchcl]['rev']
#        return None

    def __cmp__(self, other):
        return (self.depotfile > other.depotfile) - (self.depotfile <
                other.depotfile)

    @property
    def depotfile(self):
        return self._depotfile

    @property
    def revisions(self):
        return sorted(self._data.keys())

    def isdeleted(self, clnum):
        return self._data[clnum]['action'] in ['move/delete', 'delete']

    def isexec(self, clnum):
        t = self._data[clnum]['type']
        return 'xtext' == t or '+x' in t

    def issymlink(self, clnum):
        t = self._data[clnum]['type']
        return 'symlink' in t

    def iskeyworded(self, clnum):
        t = self._data[clnum]['type']
        return '+k' in t

ACTION_EDIT = ['edit', 'integrate']
ACTION_ADD = ['add', 'branch', 'move/add']
ACTION_DELETE = ['delete', 'move/delete']
SUPPORTED_ACTIONS = ACTION_EDIT + ACTION_ADD + ACTION_DELETE

class P4Changelist(object):
    def __init__(self, origclnum, clnum):
        self._clnum = clnum
        self._origclnum = origclnum

    def __repr__(self):
        return '<P4Changelist %d>' % self._clnum

    @property
    def cl(self):
        return self._clnum

    @property
    def origcl(self):
        return self._origclnum

    def __cmp__(self, other):
        return (self.cl > other.cl) - (self.cl < other.cl)

    def __hash__(self):
        """Ensure we are matching changelist numbers in sets and hashtables,
        which the importer uses to ensure uniqueness of an imported changeset"""
        return hash((self.origcl, self.cl))

    @util.propertycache
    def parsed(self):
        return self.load()

    def load(self):
        """Parse perforces awkward format"""
        files = {}
        info = parse_cl(self._clnum)
        i = 0
        while True:
            fidx = 'depotFile%d' % i
            aidx = 'action%d' % i
            ridx = 'rev%d' % i
#XXX: Handle oldChange vs change
            if fidx not in info:
                break
            files[info[fidx]] = {
                'rev': int(info[ridx]),
                'action': info[aidx],
            }
            i += 1
        return {
            'files': files,
            'desc': info['desc'],
            'user': info['user'],
            'time': int(info['time']),
        }

    def rev(self, fname):
        return self.parsed['files'][fname]['rev']

    @property
    def files(self):
        """Returns added, modified and removed files for a changelist.

        The current mapping is:

        Mercurial  | Perforce
        ---------------------
        add        | add, branch, move/add
        modified   | edit, integrate
        removed    | delete, move/delte
        """
        a, m, r = [], [], []
        for fname, info in self.parsed['files'].iteritems():
            if info['action'] in ACTION_EDIT:
                m.append(fname)
            elif info['action'] in ACTION_ADD:
                a.append(fname)
            elif info['action'] in ACTION_DELETE:
                r.append(fname)
            else:
                assert False
        return a, m, r

