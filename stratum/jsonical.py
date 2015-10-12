# Copyright 2009 New England Biolabs <davisp@neb.com>
#
# This file is part of the nebgbhist package released under the MIT license.
#
r"""Canonical JSON serialization.

Basic approaches for implementing canonical JSON serialization.

Encoding basic Python object hierarchies::

    >>> import jsonical
    >>> jsonical.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])
    '["foo",{"bar":["baz",null,1.0,2]}]'
    >>> print jsonical.dumps("\"foo\bar")
    "\"foo\bar"
    >>> print jsonical.dumps(u'\u1234')
    "\u1234"
    >>> print jsonical.dumps('\\')
    "\\"
    >>> print jsonical.dumps({"c": 0, "b": 0, "a": 0})
    {"a":0,"b":0,"c":0}
    >>> from StringIO import StringIO
    >>> io = StringIO()
    >>> json.dump(['streaming API'], io)
    >>> io.getvalue()
    '["streaming API"]'

Decoding JSON::

    >>> import jsonical
    >>> jsonical.loads('["foo", {"bar":["baz", null, 1.0, 2]}]')
    [u'foo', {u'bar': [u'baz', None, Decimal('1.0'), 2]}]
    >>> jsonical.loads('"\\"foo\\bar"')
    u'"foo\x08ar'
    >>> from StringIO import StringIO
    >>> io = StringIO('["streaming API"]')
    >>> jsonical.load(io)
    [u'streaming API']

Using jsonical from the shell to canonicalize:

    $ echo '{"json":"obj","bar":2.333333}' | python -mjsonical
    {"bar":2.333333,"json":"obj"}
    $ echo '{1.2:3.4}' | python -mjson.tool
    Expecting property name: line 1 column 2 (char 2)

"""
import datetime
import decimal
import sys
import types
import unicodedata

try:
    import json
except ImportError:
    import simplejson as json

class Encoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs.pop("sort_keys", None)
        super(Encoder, self).__init__(sort_keys=True, *args, **kwargs)

    def default(self, obj):
        """This is slightly different than json.JSONEncoder.default(obj)
        in that it should returned the serialized representation of the
        passed object, not a serializable representation.
        """
        if isinstance(obj, (datetime.date, datetime.time, datetime.datetime)):
            return '"%s"' % obj.isoformat()
        elif isinstance(obj, unicode):
            return '"%s"' % unicodedata.normalize('NFD', obj).encode('utf-8')
        elif isinstance(obj, decimal.Decimal):
            return str(obj)
        return super(Encoder, self).default(obj)

    def _iterencode_default(self, o, markers=None):
        yield self.default(o)

def dump(obj, fp, indent=None):
    return json.dump(obj, fp, separators=(',', ':'), indent=indent, cls=Encoder)

def dumps(obj, indent=None):
    return json.dumps(obj, separators=(',', ':'), indent=indent, cls=Encoder)

class Decoder(json.JSONDecoder):
    def raw_decode(self, s, **kw):
        obj, end = super(Decoder, self).raw_decode(s, **kw)
        if isinstance(obj, types.StringTypes):
            obj = unicodedata.normalize('NFD', unicode(obj))
        return obj, end

def load(fp):
    return json.load(fp, cls=Decoder, parse_float=decimal.Decimal)

def loads(s):
    return json.loads(s, cls=Decoder, parse_float=decimal.Decimal)

def tool():
    infile = sys.stdin
    outfile = sys.stdout
    if len(sys.argv) > 1:
        infile = open(sys.argv[1], 'rb')
    if len(sys.argv) > 2:
        outfile = open(sys.argv[2], 'wb')
    if len(sys.argv) > 3:
        raise SystemExit("{0} [infile [outfile]]".format(sys.argv[0]))
    try:
        obj = load(infile)
    except ValueError, e:
        raise SystemExit(e)
    dump(obj, outfile)
    outfile.write('\n')

if __name__ == '__main__':
    tool()