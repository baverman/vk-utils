#!/usr/bin/env python2
import argparse
import os.path

from itertools import groupby

from urllib import urlencode
from urlparse import parse_qs
from json import loads
import urllib2

VK_OAUTH_URL = 'https://oauth.vk.com/authorize'
VK_OAUTH_PARAMS = {
    'client_id': '3229084',
    'scope': 'messages,offline',
    'redirect_uri': 'http://oauth.vk.com/blank.html',
    'display': 'page',
    'response_type': 'token',
}

VK_METHOD_URL = 'https://api.vk.com/method/{}?{}'
TIMEOUT = 2


class VK(object):
    def __init__(self, access_token):
        self.opener = urllib2.build_opener()
        #self.opener.process_request['https'][0]._debuglevel = 1
        self.access_token = access_token

    def call(self, method, **kwargs):
        kwargs['access_token'] = self.access_token
        url = VK_METHOD_URL.format(method, urlencode(kwargs))
        result = self.opener.open(url, timeout=TIMEOUT)
        response = result.read()
        return loads(response)['response']


def get_oauth_url():
    return VK_OAUTH_URL + '?' + urlencode(VK_OAUTH_PARAMS)

def get_config(fname):
    config_dir = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    return os.path.join(config_dir, fname)

def store_settings(redirect_url):
    result = parse_qs(redirect_url.rpartition('#')[2])
    token = result['access_token'][0]
    user_id = result['user_id'][0]

    with open(get_config('vk-notify.conf'), 'w') as f:
        f.write('{}\n{}'.format(token, user_id))

def get_settings():
    token, user_id = open(get_config('vk-notify.conf')).readlines()
    token = token.strip()
    user_id = user_id.strip()
    return token, user_id

def get_users(vk, uids):
    cache_fname = get_config('vk-notify.uid.cache')
    if os.path.exists(cache_fname):
        cache = dict((int(uid), user.strip().decode('utf-8'))
            for (uid, user) in map(lambda r:r.split(':'), open(cache_fname)))
    else:
        cache = {}

    non_existing_uids = [r for r in uids if r not in cache]
    if non_existing_uids:
        users = {r['uid']: '{first_name} {last_name}'.format(**r)
            for r in vk.call('getProfiles', uids=','.join(map(str, uids)))}

        cache.update(users)

    if non_existing_uids:
        with open(cache_fname, 'w') as f:
            for r in cache.iteritems():
                f.write(u'{}:{}\n'.format(*r))

    return cache

def get_new_messages(token):
    vk = VK(token)
    result = vk.call('messages.get', count=20, time_offset=0)

    messages = result[1:]
    last_message_fname = get_config('vk-notify.last.message')

    if any(not r['read_state'] for r in messages):
        if os.path.exists(last_message_fname):
            last_message = int(open(last_message_fname).read())
        else:
            last_message = 0

        users = get_users(vk, set([r['uid'] for r in messages]))
        for m in reversed(messages):
            if m['mid'] > last_message:
                yield users[m['uid']], m['title'] if 'chat_id' in m else None, m
    else:
        if messages:
            print >>open(last_message_fname, 'w'), messages[0]['mid']

def notify():
    from glib import markup_escape_text
    import pynotify
    pynotify.init('vk-notify')

    try:
        token, _ = get_settings()
        user_messages = get_new_messages(token)

        tm = 5000
        for (user, title), g in groupby(user_messages, lambda (u, t, _):(u, t)):
            messages = map(markup_escape_text, (r['body'] for _, _, r in g))
            ntitle = markup_escape_text(user)
            if title:
                ntitle = u'{} (<small>{}</small>)'.format(ntitle, markup_escape_text(title))
            n = pynotify.Notification(ntitle, u'\n'.join(messages))
            n.set_timeout(tm)
            n.show()
            tm += 2000

    except Exception as e:
        n = pynotify.Notification('VK', markup_escape_text(str(type(e))))
        n.set_timeout(5000)
        n.show()
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--set-token', dest='token')

    parser.add_argument('-r', '--request-token', dest='request_token', action='store_true')

    args = parser.parse_args()

    if args.request_token:
        print get_oauth_url()
    if args.token:
        store_settings(args.token)
    else:
        notify()
