#!/usr/bin/python

import time
import urllib.request
import urllib.parse
import subprocess
import datetime


hosts = [
	'milan.podgorny.cz',
	'mrtvola.asterix.cz',
	'root.cz',
	'rpodgorny.podgorny.cz',
	'simir.podgorny.cz',
]


def ping(host):
	cmd = 'ping6 -c 4 %s' % host
	res = subprocess.call(cmd, shell=True)
	return res == 0
#enddef


def send(src, dst, dt, key, value):
	url = 'http://localhost:8755/save'

	d = {
		'src': src,
		'dst': dst,
		'datetime': dt,
		'key': key,
		'value': value,
	}
	url = '%s?%s' % (url, urllib.parse.urlencode(d, True))

	u = urllib.request.urlopen(url).read().decode('utf-8')
#enddef


def main():
	while 1:
		data = []

		for host in hosts:
			src = 'test'
			dst = host
			dt = datetime.datetime.now()

			res = ping(host)

			data.append((src, dst, dt, 'ping', res))
		#endfor

		for d in data:
			send(*d)
		#endfor

		time.sleep(60)
	#endwhile
#enddef


if __name__ == '__main__':
	main()
#endif
