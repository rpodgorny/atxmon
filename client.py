#!/usr/bin/python

import time
import urllib.request
import urllib.parse
import subprocess
import datetime
import concurrent.futures


hosts = [
	'milan.podgorny.cz',
	'mrtvola.asterix.cz',
	'root.cz',
	'rpodgorny.podgorny.cz',
	'simir.podgorny.cz',
]
for i in range(200): hosts.append('mj%d.asterix.cz' % i)

contains = [
	('https://wheelcat.cz', 'Adama Musila'),
]



def ping(host):
	cmd = 'ping6 -c 4 %s >/dev/null 2>&1' % host
	res = subprocess.call(cmd, shell=True)
	return res == 0
#enddef


def url_contains(url, s):
	cmd = 'curl "%s" 2>/dev/null | grep "%s" >/dev/null 2>&1' % (url, s)
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
	data = []
	ex = concurrent.futures.ThreadPoolExecutor(20)

	while 1:
		fs = {}

		for host in hosts:
			src = 'test'
			dst = host
			dt = datetime.datetime.now()

			#res = ping(host)
			f = ex.submit(ping, host)
			fs[f] = ('ping', src, dst, dt)
			#print('%s %s' % (host, res))

			#data.append((src, dst, dt, 'ping', res))
		#endfor

		for url, s in contains:
			src = 'test'
			dst = url
			dt = datetime.datetime.now()

			f = ex.submit(url_contains, url, s)
			fs[f] = ('url_contains', src, dst, dt)
		#endfor

		for f in concurrent.futures.as_completed(fs.keys()):
			action, src, dst, dt = fs[f]
			res = f.result()
			data.append((src, dst, dt, action, res))
			print('%s %s %s' % (action, dst, res))
		#endfor

		try:
			for d in data:
				send(*d)
			#endfor

			data = []
		except:
			print('failed to send data')
		#endtry

		print('data size is %d, sleeping' % len(data))
		time.sleep(60)
	#endwhile

	ex.shutdown()
#enddef


if __name__ == '__main__':
	main()
#endif
