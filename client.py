#!/usr/bin/python

import time
import urllib.request
import urllib.parse
import subprocess
import datetime
import concurrent.futures
import json
import re


pings = [
	'milan.podgorny.cz',
	'mrtvola.asterix.cz',
	'root.cz',
	'rpodgorny.podgorny.cz',
	'simir.podgorny.cz',
]
for i in range(200): pings.append('mj%d.asterix.cz' % i)

contains = [
	('https://wheelcat.cz', 'Adama Musila'),
]

iperfs = [
	'admiral.podgorny.cz',
]



def ping(host):
	cmd = 'ping6 -c 10 -q %s 2>/dev/null' % host
	try:
		out = subprocess.check_output(cmd, shell=True).decode()
	except:
		return {}
	#endtry

	packet_loss = None
	rtt_avg = None
	for line in out.split('\n'):
		if 'packet loss' in line:
			# TODO: compile this?
			m = re.match('.+, (\d+)% packet loss,.+', line)
			packet_loss = int(m.groups()[0])
		#endif

		if 'rtt min/avg/max/mdev' in line:
			# TODO: compile this?
			m = re.match('rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms', line)
			_, rtt_avg, _, _ = [float(i) for i in m.groups()]
		#endif
	#endfor

	return {'packet_loss': packet_loss, 'rtt_avg': rtt_avg}
#enddef


def iperf3(host):
	cmd = 'iperf3 -c %s -J -R -P 5' % host
	out = subprocess.check_output(cmd, shell=True).decode()
	res = json.loads(out)
	ret = res['end']['sum_received']['bits_per_second']
	return {'bits_per_second': ret}
#enddef


def url_contains(url, s):
	cmd = 'curl "%s" 2>/dev/null | grep "%s" >/dev/null 2>&1' % (url, s)
	res = subprocess.call(cmd, shell=True)
	return {'ok': res == 0}
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

		for host in pings:
			src = 'test'
			dst = host
			dt = datetime.datetime.now()

			f = ex.submit(ping, host)
			fs[f] = ('ping', src, dst, dt)
		#endfor

		for url, s in contains:
			src = 'test'
			dst = url
			dt = datetime.datetime.now()

			f = ex.submit(url_contains, url, s)
			fs[f] = ('url_contains', src, dst, dt)
		#endfor

		for host in iperfs:
			src = 'test'
			dst = host
			dt = datetime.datetime.now()

			f = ex.submit(iperf3, host)
			fs[f] = ('iperf3', src, dst, dt)
		#endfor

		for f in concurrent.futures.as_completed(fs.keys()):
			action, src, dst, dt = fs[f]
			res = f.result()

			for k, v in res.items():
				data.append((src, dst, dt, action, k, v))
				print('%s %s %s %s' % (action, dst, k, v))
			#endfor
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
