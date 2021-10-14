#!/usr/bin/python

LIBRARY_ID = '' # Zotero library ID
LIBRARY_TYPE = 'group'
CACHE_DIR = '' # absolute path on the server
IMG_DIR = '' # absolute path on the server
IMG_URL = '' # URL path corresponding to IMG_DIR


"""Zotero toolkit

    CGI script providing tools to support meta-analysis using a library managed
    in Zotero.

    Copyright 2019-2021, Eric Thrift

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""

import json
import sys
import cgi
import codecs
import base64
import hashlib
import glob
import os
import textwrap
import urllib.parse

from pyzotero import zotero
from cachier import cachier

import cgitb
cgitb.enable()

# import BEFORE pandas (-->numpy) to avoid segfault
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import pandas as pd
import matplotlib.pyplot as plt

plt.style.use('seaborn')
plt.rcParams["figure.figsize"] = [8, 5]

sys.stdout = codecs.getwriter('utf8')(sys.stdout.buffer)
sys.stderr = sys.stdout


HTML_HEADER = """<html><head>
<link rel="stylesheet" href="https://unpkg.com/tachyons@4.12.0/css/tachyons.min.css"/>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>th, td{padding:0.5em;}</style>
</head>
<body><div class="pa4 sans-serif f5">
"""

QUERY_BUTTON = """<p class="center mw4 measure"><a href="/cgi-bin/zoterotags.py?{}" class="f6 link ph3 pv3 mb2 dib bg-black-70 hover-bg-black bg-animate white pointer mt4 br2-ns">Revise query</a><br><small class="f6 black-60 db mb2">Reset the form with current tag list(s) pre-loaded</small></p>"""

HTML_FOOTER = """
</div>
</body>
</html>
"""

FORM = """<head>
<link rel="stylesheet" href="/static/tachyons.min.css"/>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<div class="pa4 sans-serif f5">
  <form class="bg-light-gray mw7 center pa4 br2-ns ba b--black-10" action="/cgi-bin/zoterotags.py" method="get">
    <h1>Zotero tags query</h1>
    <fieldset class="cf bn ma0 pa0">
      <legend class="pa0 mb3 f4 black-80">This script will query the Zotero library to produce tables or graphs identifying the number of items associated with specific tags.</legend>
      <div class="measure">

        <label for="tags_x" class="f6 b db mb2">X axis tags <span class="normal black-60">(required)</span></label>
        <textarea rows="8" class="input-reset ba b--black-20 pa2 mb2 db w-100" style="resize:vertical;" placeholder="tag a \r\ntag b" type="text" name="tags_x" value="" id="tags_x">{tags_x}</textarea>
        <small id="pages-desc" class="f6 black-60 db mb2">Provide a list of tags to include in the results, one per line.</small>

        <label for="tags_y" class="f6 b db mb2 mt3">Y axis tags <span class="normal black-60">(optional)</span></label>
        <textarea rows="8" class="input-reset ba b--black-20 pa2 mb2 db w-100" style="resize:vertical;"  placeholder="tag a \r\ntag b" type="text" name="tags_y" value="" id="tags_y">{tags_y}</textarea>
        <small class="f6 black-60 db mb2">Provide a list of tags to include in the results, one per line. If both <code>x</code> and <code>y</code> axes are specified, the query results will include the number of items matching the intersection of each <code>(x,y)</code> pair.</small>

        <label for="filter" class="f6 b db mb2 mt3">Filter <span class="normal black-60">(optional)</span></label>
        <textarea class="input-reset ba b--black-20 pa2 mb2 db w-100" placeholder="tag a \r\ntag b" type="text" name="filter" value="" id="filter">{filter}</textarea>
        <small class="f6 black-60 db mb2">Provide a list of tags to to filter the results, one per line. These tags will not be included explicitly in the resulting dataset, but only items that match ALL the tags in this list will be included in the results. Use a hyphen prefix for tags to be excluded, e.g., <code>-ignore</code> to prevent items with the tag <code>ignore</code> from being listed in the results.</small>

        <label for="format" class="f6 b db mb2 mt3">Output format <span class="normal black-60">(required)</span></label>
        <input type="radio" id="json" name="format" value="json">
        <label for="json">json</label>
        <input type="radio" id="table" name="format" value="table">
        <label for="json">table</label>
        <input type="radio" id="image" name="format" value="image" checked>
        <label for="json">graph</label>

        <h3>Graph options</h3>

        <label for="image_type" class="f6 b db mb2">Image type</label>
        <input type="radio" id="png" name="image_type" value="png">
        <label for="png">png</label>
        <input type="radio" id="svg" name="image_type" value="svg" checked>
        <label for="svg">svg</label>
        <input type="radio" id="pdf" name="image_type" value="svg">
        <label for="svg">pdf</label>
        <small class="f6 black-60 db mb2">SVG images (default) can be resized without loss of quality, but may not display properly in some applications.</small>

        <label for="image_type" class="f6 b db mb2 mt3">Graph type</label>
        <input type="radio" id="barh" name="graph_format" value="barh" checked>
        <label for="barh">Horizontal bar</label>
        <input type="radio" id="bar" name="graph_format" value="bar">
        <label for="bar">Vertical bar</label>
        <small class="f6 black-60 db mb2">Use horizontal bar graphs if the labels are longer.</small>

        <label for="values_type" class="f6 b db mb2 mt3">Values type</label>
        <input type="radio" id="raw" name="values_type" value="raw" class="mt3" checked>
        <label for="raw">Raw values</label>
        <small class="f6 black-60 db mb2">Represent values in <code>(x,y)</code> unions as raw numbers (default).</small>

        <input type="radio" id="percent" name="values_type" value="percent" class="mt3">
        <label for="percent">Percent of category</label>
        <small class="f6 black-60 db mb2">Represent values in <code>(x,y)</code> unions as a percentage of the total number of items in the library matching tag <code>x</code>. The total is adjusted to include only items matching the filter criteria given above.</small>

        <input type="radio" id="percent_matches" name="values_type" value="percent_matches" class="mt3">
        <label for="percent_matches">Percent of matches</label>
        <small class="f6 black-60 db mb2">Represent values in <code>(x,y)</code> unions as a percentage of the total number of items in current result set. This will result in stacked bar graphs that add up to 100%.</small>

        <input type="checkbox" id="sort" name="sort" class="mt3" checked>
        <label for="sort">Sort</label>
        <small class="f6 black-60 db mb2">Sort data according to the <code>y</code> axis. (EXPERIMENTAL: Generally leave checked.)</small>

        <input type="checkbox" id="subplots" name="subplots" class="mt3">
        <label for="subplots">Subgraphs</label>
        <small class="f6 black-60 db mb2">If both <code>x</code> and <code>y</code> are arrays, generate a series of graphs, one for each value in <code>x</code>.</small>

        <input type="checkbox" id="label_bars" name="label_bars" class="mt3">
        <label for="subplots">Label bars with data</label>
        <small class="f6 black-60 db mb2">Print source values on each bar in a bar graph. Currently only works for horizontal bar graphs.</small>

        <input type="checkbox" id="transpose" name="transpose" class="mt3">
        <label for="transpose">Transpose</label>
        <small class="f6 black-60 db mb2">Transpose <code>x</code> and <code>y</code> axes in the resulting table or graph.</small>

        <input type="checkbox" id="stack" name="stack" class="mt3" >
        <label for="stack">Stack</label>
        <small class="f6 black-60 db mb2">Present graph results in stacked format.</small>

        <input type="checkbox" id="square" name="square" class="mt3" >
        <label for="square">Square</label>
        <small class="f6 black-60 db mb2">Create a square graph.</small>

        <input class="f6 f5-l button-reset pv3 tc bn bg-animate bg-black-70 hover-bg-black white pointer w-100 w-25-m w-20-l br2-ns mt3" type="submit" value="submit" />
      </div>
    </fieldset>
  </form>
</div>
</body>
</html>
"""


def _strip(tag):
    new_tag = tag.strip('!@#$%^&*_+')
    if new_tag == '': # e.g., if the source tag is just "!" or "**"
        return tag
    return new_tag

def editable_query(p):
    """Return a query dict with format=none to return the form."""
    q = {'format': None}
    for i in ['filter', 'tags_x', 'tags_y']:
        if isinstance(p[i], list): # non-empty value
            q[i] = '\r\n'.join(p[i])
        else:
            q[i] = '' # strings so the form inputs don't say "None"

    return q

def parse_query():
    """Parse the incoming cgi query, returning a dict."""
    q = cgi.FieldStorage(keep_blank_values=True)
    # fields that take a single value
    simplefields = [ 'edit_query', 'format', 'values_type', 'graph_format',
        'stack', 'purge', 'purge_data', 'purge_images', 'image_type', 'transpose', 
        'sort', 'subplots', 'square', 'label_bars', 'label_int']
    # fields that should be split on newlines
    listfields = ['filter', 'tags_x', 'tags_y']
    params = {}
    for k in simplefields + listfields:
        v = q.getvalue(k, None)
        if v and k in listfields:
            params[k] = v.split('\r\n')
        else:
            params[k] = v
    return params


def get_count(tags_x, tag_filter, rows=True):
    """Generate a data table containing counts of items per tag.

    TAG_X is a list of tags, separated by newlines.
    """
    if rows:
        out = []
    else:
        out = {}
    for x in tags_x:
        if tag_filter:
            tags = frozenset([x] + tag_filter)
        else:
            tags = frozenset([x])
        t = query_zotero(tags)
        if rows:
            out.append({'tag': _strip(x), 'count': len(t)})
        else:
            out[_strip(x)] = len(t)
    return out


@cachier(cache_dir=CACHE_DIR, pickle_reload=False)
def query_zotero(tags):
    """Query Zotero.

    The tags parameter is an immutable set, so the function can be hashed and stored in a cache. 
    The cache does not expire, so it needs to be invalidated using the purge() method."""
    zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE)
    try:
        t = zot.everything(zot.items(tag=tags, format='versions', limit=None))
    except:
        error('Zotero server error')
    return t


def get_union(tags_x, tags_y, tag_filter):
    """Generate a data table containing an array of tag correlations.

    Each of TAG_X and TAG_Y is a list of tags, separated by newlines.

    Use the `filter` argument as a global filter to limit the results to
    items that match a specific tag or tags (this argument can be specified more
    than once, in which case ALL tags must be matched to be included in the
    result set). To exclude items that match a given tag, use a negative
    operator prefix (e.g., "-tag to exclude").
    """

    rows = []

    for y in tags_y:
        row = {'tag': _strip(y)}
        for x in tags_x:
            if tag_filter:
                tags = frozenset([x,y] + tag_filter)
            else:
                tags = frozenset([x,y])
            t = query_zotero(tags)
            row[_strip(x)] = len(t)
        rows.append(row)

    return rows


def percentify(p, matches=False):
    """Construct a data table in which values are percentages of total.

    The "total" in this case is the overall number of items in the
    Zotero library matching each tag.

    """
    raw = get_union(p['tags_x'], p['tags_y'], p['filter'])
    if matches:
        totals = {}
        for row in raw:
            totals[row['tag']] = sum([v for k,v in row.items() if k != 'tag'])
    else:
        totals = get_count(p['tags_x'], p['filter'], rows=False)
    percent = []
    for row in raw:
        newrow = {'tag': row['tag']}
        for tag in row:
            if tag == 'tag':
                continue
            if matches:
                # don't use integers if we want the numbers to add up to 100
                newrow[tag] = int(row[tag])/int(totals[row['tag']])*100
            elif totals[tag] == 0:
                newrow[tag] = 0
            else:
                newrow[tag] = int(row[tag])/int(totals[tag])*100
        percent.append(newrow)
    return percent

def get_data(p):
    """Execute Zotero queries and return a raw data table."""
    if p['values_type'] == 'percent' and p['tags_x'] and p['tags_y']:
        return percentify(p)
    if p['values_type'] == 'percent_matches' and p['tags_x'] and p['tags_y']:
        return percentify(p, matches=True)
    if p['tags_x'] and p['tags_y']:
        return get_union(p['tags_x'], p['tags_y'], p['filter'])
    if p['tags_x']:
        return get_count(p['tags_x'], p['filter'])
    return error("no data")

def error(message):
    """Exit with an error message."""
    sys.exit(message)

def hash_query(p):
    """Create a unique hash ID for the current query."""
    enc = json.dumps(p, sort_keys=True).encode()
    return hashlib.sha1(enc).hexdigest()

def graph(p):
    """Return an html img tag for a graph."""
    h = hash_query(p)
    fmt = p['image_type'] or 'svg'
    img = '{}.{}'.format(h, fmt)
    path = os.path.join(IMG_DIR, img)
    url = '/'.join([IMG_URL, img])
    if not os.path.exists(path):
        build_graph(p, path)
    if fmt in ('pdf'):
        return '<div class="tc"><a href="{}" />PDF: {}</div>'.format(url, h)
    return '<div class="tc"><img src="{}" id="{}"/></div>'.format(url, h)

def build_graph(p, path):
    """Create a graph image and store on disk."""

    df = dataframe(p)
    stacked = p['stack'] or False
    square = p['square'] or False
    label_bars = p['label_bars'] or False

    # this is the width of bars. At 100% they touch one another.
    width=0.85
    if stacked:
        width=0.6
    graph_format = p['graph_format'] or 'barh'
    if square:
        u = df.plot(kind=graph_format, width=width, stacked=stacked, rot=0, figsize=(4,4))
    else:
        u = df.plot(kind=graph_format, width=width, stacked=stacked, rot=0)
    plt.xlabel('')
    plt.ylabel('')
    if label_bars and graph_format == 'barh':
        if p['label_int']:
            NUM = "{:}"
        else:
            NUM = "{:.1f}"
        for patch in u.patches:
            y_offset = patch.get_height() / 2
            u.annotate(NUM.format(patch.get_width()), (patch.get_x() + patch.get_width(), 
                                                       patch.get_y() + patch.get_height() / 2), xytext=(2,0), 
                                                       textcoords='offset points', fontsize=7, va='center')


    # multiple columns with long labels cause the graph itself to get narrower
    # FIXME: Use a threshold for maximum label length. Set column number
    # so that the total width per row is <= 60 chars
    u.legend(frameon=False, loc='upper center', bbox_to_anchor=(0.5,-0.05), ncol=2)
    plt.tight_layout()
    u.figure.savefig(path, bbox_inches="tight")
    return True

def purge_data():
    query_zotero.clear_cache()
    print('Query cache purged')
    return

def purge_images():
    images = glob.glob(IMG_DIR + '/*')
    for i in images:
        os.remove(i)
    print('Image cache purged')
    return

def purge():
    """Clear the query cache and delete stored graph images."""
    query_zotero.clear_cache()

    # print('Content-Type: text/plain\r\n')
    print('Query and image cache purged')
    return

def wrap(data):
    """Wrap data labels for 'tag' index field."""
    for d in data:
        d['tag'] = '\n'.join(textwrap.wrap(d['tag'], width=16))
    return data

def dataframe(p):
    """Generate a pandas dataframe."""
    data = get_data(p)
    wrap(data)
    df = pd.DataFrame.from_records(data, index='tag')
    if p['sort'] or False:
        cols = df.columns.values.tolist()
        df = df.sort_values(by=cols)
    else:
        # This reorders the columns by manually supplied order
        # FIXME: Move the strip function so we don't do it twice
        df = df.reindex(columns=[_strip(x) for x in p['tags_x']])

    if p['transpose']:
        df = df.T
    return df

def table(p):
    df = dataframe(p)
    html = df.to_html(classes='collapse ba br2 b--black-10 pv2 ph3 mt4 center')
    return html.replace('\\n', ' ')

def print_json(p):
    """Print a json representation of the raw query response data."""
    data = get_data(p)
    print('Content-Type: application/json\r\n')
    print(json.dumps(data, indent=4, sort_keys=True))
    return

def print_html(content, new_query=False):
    """Print content as an html document with matching HTTP header."""
    print(HTML_HEADER)
    print(content)
    if new_query:
        print(QUERY_BUTTON.format(new_query))
    print(HTML_FOOTER)
    return

def run():
    p = parse_query()
    q = editable_query(p)
    e = urllib.parse.urlencode(q)

    if p['purge']:
        return purge()
    if p['purge_data']:
        return purge_data()
    if p['purge_images']:
        return purge_images()

    if p['format'] == 'json':
        return print_json(p)

    if p['format'] == 'table':
        return print_html(table(p), new_query=e)

    if p['format'] == 'image':
        if p.get('subplots', False) and isinstance(p['tags_x'], list):
            # manually generate each graph; keep same sort order
            p['sort'] = False
            graphs = []
            tags_x = p['tags_x'].copy()
            for x in tags_x:
                p['tags_x'] = [x]
                graphs.append(graph(p))
            content = ''.join(graphs)
        else:
            content = graph(p)
        return print_html(content, new_query=e)

    return print_html(FORM.format(**q))


if __name__ == '__main__':
    print('Content-Type: text/html\r\n')
    print('<!DOCTYPE html>\r\n')
    run()
