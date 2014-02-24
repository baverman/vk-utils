#!/usr/bin/env python2
import sys
import os
import re
import argparse
import shlex

from urllib2 import build_opener, HTTPCookieProcessor
from urllib import urlencode
from cookielib import CookieJar
from htmlentitydefs import name2codepoint

from netrc import netrc

from lxml import html
from ast import literal_eval

class ErrorMessage(Exception): pass

HD_RES = {
    1: 360,
    2: 480,
    3: 720,
}

cj = CookieJar()
opener = build_opener(HTTPCookieProcessor(cj))

def decode_html_entities(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            try:
                text = unichr(name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text
    return re.sub("&#?\w+;", fixup, text.decode('utf-8')).encode('utf-8')

def login():
    result = netrc().authenticators('vk.com')
    if not result:
        raise ErrorMessage('You have no entries in ~/.netrc file associated with vk.com')

    email, _, pwd = result

    resp = opener.open("http://vk.com")
    root = html.parse(resp)

    params = {node.attrib['name']:node.attrib.get('value', '')
        for node in root.xpath('//form//input[@type!="submit"]')}

    params['email'] = email
    params['pass'] = pwd

    opener.open(root.xpath('//form')[0].attrib['action'], urlencode(params))

def get_url(url):
    _, _, vid = url.rpartition('/')
    if not vid.startswith('video'):
        print >> sys.stderr, 'Bad url:', url
        sys.exit(1)

    params = {
        'act': 'show',
        'al': '1',
        'list': '',
        'module': 'video',
        'video': vid[5:].partition('?')[0]
    }

    resp = opener.open('http://vk.com/al_video.php', urlencode(params))
    # print resp.read()
    match = re.search('var\svars\s=\s(\{.+?\});', resp.read())
    data = literal_eval(match.group(1).decode('windows-1251').encode('utf-8').replace('\\"', '"'))

    if isinstance(data['host'], basestring) and 'vkadre.ru' in data['host'] and not data['no_flv']:
        vurl = "http://{host}/assets/videos/{vtag}{vkid}.vk.flv".format(**data)
    else:
        res = HD_RES[data.get('hd', 1)]
        vurl = "http://cs{host}.vk.com/u{uid}/videos/{vtag}.{res}.mp4".format(res=res, **data)

    fname = decode_html_entities(data['md_title'].strip()) + '.' + vurl.rpartition('.')[2]
    fname = fname.replace('/', '-')
    return {'url':vurl, 'fname':fname}

def run_cmd(cmd, data):
    cmdlist = [r.format(**data) for r in shlex.split(cmd)]
    os.execvp(cmdlist[0], cmdlist)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--exec', dest='cmd')
    parser.add_argument('url')

    args = parser.parse_args()

    login()
    result = get_url(args.url)

    if args.cmd:
        run_cmd(args.cmd, result)
    else:
        print result['url']
