#!/usr/bin/python

import time
import requests
import subprocess
import json
import re
import sys
import socket
from utils import *
import jinja2
import threading
import random


SERVER_URL = 'http://admiral.podgorny.cz:5000/save'
TESTS_FN = 'tests.conf'
SEND_INTERVAL = 20
TESTS_MAX = 10  # TODO: rename to THREADS_MAX?


def load_tests(fn):
	ret = []

	with open(fn, 'r') as f:
		t = jinja2.Template(f.read())
		rendered = t.render()
	#endwith

	for line in rendered.splitlines():
		line = line.strip()

		if not line: continue
		if line.startswith('#'): continue

		interval, test, *args = line.split(';')
		if interval.endswith('m'):
			interval = float(interval[:-1]) * 60
		else:
			interval = float(interval)
		#endif

		ret.append((interval, test, args))
	#endfor

	return ret
#enddef


def load():
	ret = {}

	with open('/proc/loadavg', 'r') as f:
		loads = [float(i) for i in f.read().split()[:3]]
		ret['1min'] = loads[0]
		ret['5min'] = loads[1]
		ret['15min'] = loads[2]
	#endwith

	return ret
#enddef


def ping(host, ipv6=False):
	if ipv6:
		cmd = 'ping6 -c 5 -q %s 2>/dev/null' % host
	else:
		cmd = 'ping -c 5 -q %s 2>/dev/null' % host
	#endif

	try:
		out = subprocess.check_output(cmd, shell=True).decode()
	except:
		return {'ok': 0}
	#endtry

	packet_loss = None
	rtt_avg = None
	for line in out.splitlines():
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

	return {'ok': 1, 'packet_loss': packet_loss, 'rtt_avg': rtt_avg}
#enddef


def ping6(host):
	return ping(host, ipv6=True)
#enddef


def iperf3(host):
	ret = {}
	ok = 1

	for direction in ['up', 'down']:
		if direction == 'down':
			cmd = 'timeout 20 iperf3 -c %s -J -R -P 5' % host
		else:
			cmd = 'timeout 20 iperf3 -c %s -J -P 5' % host
		#endif

		try:
			out = subprocess.check_output(cmd, shell=True).decode()
			res = json.loads(out)
			bits_per_second = res['end']['sum_received']['bits_per_second']
			ret['%s/bits_per_second' % direction] = bits_per_second
		except:
			ok = 0
		#endtry
	#endfor

	ret['ok'] = ok
	return ret
#enddef


def url_contains(url, contains=None):
	r = requests.get(url)

	if contains in r.text:
		ok = 1
	else:
		ok = 0
	#endif

	return {'ok': ok}
#enddef


def send(url, data):
	requests.post(url, data=json.dumps(data))
#enddef


class TestThread(threading.Thread):
	def __init__(self, fn, *args):
		threading.Thread.__init__(self)

		self.fn = fn
		self.args = args
		self.res = None
	#enddef

	def run(self):
		self.res = self.fn(*self.args)
	#enddef
#endclass


TEST_MAP = {
	'load': load,
	'ping': ping,
	'ping6': ping6,
	'url_contains': url_contains,
	'iperf3': iperf3,
}


def main():
	data = []
	last_sent = 0

	src = socket.gethostname()
	tests = load_tests(TESTS_FN)

	threads = {}

	last_run = {}
	for interval, test, args in tests:
		# TODO: cut-n-pasted to below
		test_name = '%s/%s' % (src, test)
		if args:
			test_name = '%s/%s' % (test_name, '/'.join(args))
		#endif

		last_run[test_name] = time.time() - interval * random.random()
	#endfor

	while 1:
		t = time.time()

		for test_name, thr in threads.copy().items():
			if thr.is_alive(): continue
			res = thr.res
			if res is None: continue

			for res_name, v in res.items():
				k_full = '%s/%s' % (test_name, res_name)
				data.append((k_full, v, t))
				print('%s=%s' % (k_full, v))
			#endfor

			thr.join()
			del threads[test_name]
		#endfor

		for interval, test, args in tests:
			# TODO: cut-n-pasted from above
			test_name = '%s/%s' % (src, test)
			if args:
				test_name = '%s/%s' % (test_name, '/'.join(args))
			#endif

			if t < last_run[test_name] + interval: continue
			if len(threads) >= TESTS_MAX: break

			print('--> %s (%s/%s)' % (test_name, len(threads) + 1, TESTS_MAX))

			fn = TEST_MAP[test]
			thr = TestThread(fn, *args)
			thr.start()
			threads[test_name] = thr
			last_run[test_name] = t
		#endfor

		if data and t > last_sent + SEND_INTERVAL:
			try:
				send(SERVER_URL, data)
				data = []
				last_sent = t
			except Exception as e:
				print('failed to send data: %s -> %s' % (str(e), len(data)))
			#endtry
		#endif

		time.sleep(1)
	#endwhile
#enddef


if __name__ == '__main__':
	main()
#endif
