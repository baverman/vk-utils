#!/usr/bin/env python2
import argparse
import os.path

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


class VK(object):
    def __init__(self, access_token):
        self.opener = urllib2.build_opener()
        self.access_token = access_token

    def call(self, method, **kwargs):
        kwargs['access_token'] = self.access_token
        url = VK_METHOD_URL.format(method, urlencode(kwargs))
        return loads(self.opener.open(url).read())['response']


def get_oauth_url():
    return VK_OAUTH_URL + '?' + urlencode(VK_OAUTH_PARAMS)

def get_config_fname():
    config_dir = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    return os.path.join(config_dir, 'vk-notify.conf')

def store_settings(redirect_url):
    result = parse_qs(redirect_url.rpartition('#')[2])
    token = result['access_token'][0]
    user_id = result['user_id'][0]

    with open(get_config_fname(), 'w') as f:
        f.write('{}\n{}'.format(token, user_id))

def get_settings():
    token, user_id = open(get_config_fname()).readlines()
    token = token.strip()
    user_id = user_id.strip()
    return token, user_id

def notify():
    from glib import markup_escape_text
    import pynotify
    pynotify.init('vk-notify')

    try:
        token, _ = get_settings()
        vk = VK(token)
        result = vk.call('messages.get', filters='1', count=10)
        count = result[0]
        if count:
            messages = result[1:]
            uids = ','.join(str(r['uid']) for r in messages)
            users = {r['uid']: '{first_name} {last_name}'.format(**r) for r in vk.call('getProfiles', uids=uids)}

            for uid, name in users.iteritems():
                title = markup_escape_text(name)
                msg = []
                for m in messages:
                    if m['uid'] == uid:
                        msg.append(markup_escape_text(m['body']))

                n = pynotify.Notification(title, u'\n'.join(msg))
                n.set_timeout(5000)
                n.show()
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