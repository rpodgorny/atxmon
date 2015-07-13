#!/usr/bin/python3

import sys
import flask
import json
import datetime
import threading
import subprocess
import logging
import time
import os
import re


HISTORY_LEN = 10

# TODO: globals are shit
app = flask.Flask(__name__)
data = []
data_last = {}
evts = []  # TODO: this is shitty name
last_vals = {}  # TODO: shitty name


# TODO: ugly name, ugly functionality
def normalize(s):
	return s.replace('/', '__').replace(' ', '_').replace(':', '_')
#enddef

def load_alerts(fn):
	ret = []
	with open(fn, 'r') as f:
		for line in f:
			line = line.strip()
			if not line: continue

			reg_exp, operator, value = line.split(' ')
			value = int(value)

			ret.append((reg_exp, operator, value))
		#endfor
	#endwith
	return ret
#enddef

def load_events(fn):
	ret = []
	with open(fn, 'r') as f:
		for line in f:
			line = line.strip()
			if not line: continue

			reg_exp, operator, value = line.split(' ')
			value = int(value)

			ret.append((reg_exp, operator, value))
		#endfor
	#endwith
	return ret
#enddef

@app.route('/')
def index():
	return 'index'
#enddef

@app.route('/save_old')
def save_old():
	k = flask.request.args.get('k')
	v = flask.request.args.get('v')
	t = float(flask.request.args.get('t'))
	p = (k, v, t)
	#data.append(p)
	data_last[k] = (v, t)
	return str(p)
#enddef

@app.route('/save', methods=['GET', 'POST'])
def save_many():
	d = flask.request.get_json(force=True)
	print('will save %s entries' % len(d))

	data.extend(d)

	for i in d:
		k = i['path']
		v = i['value']
		t = i['time']
		if not k in data_last: data_last[k] = []
		data_last[k].insert(0, (v, t))
		data_last[k] = data_last[k][:HISTORY_LEN]
	#endfor

	return 'ok'
#enddef

@app.route('/show')
def show():
	x = []
	for k in sorted(data_last.keys()):
		v, t = data_last[k][0]
		t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
		x.append((k, v, t))
	#endfor

	return flask.render_template('show.html', data_last=x)
#enddef

@app.route('/alerts')
def alerts():
	alerts = load_alerts('alerts.conf')

	x = []
	for reg_exp, operator, value in alerts:
		for k in sorted(data_last.keys()):
			if not re.match(reg_exp, k): continue

			v, t = data_last[k][0]

			if operator == '==':
				if v != value: continue
			elif operator == '!=':
				if v == value: continue
			else:
				raise Exception('unknown operator %s' % operator)
			#endif

			t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
			x.append((k, v, t))
		#endfor
	#endfor

	return flask.render_template('alerts.html', data_last=x)
#enddef

@app.route('/events'):
def events():
	x = []
	for k, v, t in evts:
		t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
		x.append((k, v, t))
	#endfor

	return flask.render_template('events.html', data_last=x)
#enddef

@app.route('/show_last/<path:test>')
def show_last(test):
	x = []
	for v, t in data_last[test]:
		t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
		x.append((v, t))
	#endfor

	return flask.render_template('show_last.html', data_last=x)
#enddef

class MyThread(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self, daemon=False)

		self._run = True
	#enddef

	def run(self):
		logging.info('thread run')

		events = load_events('events.conf')

		while self._run:
			while data:
				i = data.pop(0)
				k = i['path']
				v = i['value']
				t = i['time']
				interval = i['interval']
				print(k, v, t, interval)

				if v == last_vals.get(k): continue
					for reg_exp, operator, value in events:
						if not re.match(reg_exp, k): continue

						if operator == '==':
							if v != value: continue
						elif operator == '!=':
							if v == value: continue
						else:
							raise Exception('unknown operator %s' % operator)
						#endif

						print('new event: %s %s' % (k, v))
						evts.append((k, v, t))
					#endfor
				#endif

				fn = normalize(k)

				if not os.path.isfile('rrd/%s.rrd' % fn):
					cmd = 'rrdtool create rrd/%s.rrd --start 0 --step %d DS:xxx:GAUGE:%d:U:U' % (fn, interval, interval * 2)
					cmd += ' RRA:AVERAGE:0.999:1:100 RRA:AVERAGE:0.999:100:100'
					print(cmd)
					subprocess.check_call(cmd, shell=True)
				#endif

				#cmd = 'rrdtool update rrd/%s.rrd %d:%s' % (fn, int(t - 1), v)
				#print(cmd)
				#subprocess.check_call(cmd, shell=True)

				cmd = 'rrdtool update rrd/%s.rrd %d:%s' % (fn, int(t), v)
				print(cmd)
				subprocess.check_call(cmd, shell=True)

				cmd = 'rrdtool graph png/%s__10min.png --end now --start end-10m --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
				print(cmd)
				subprocess.check_call(cmd, shell=True)

				cmd = 'rrdtool graph png/%s__1h.png --end now --start end-1h --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
				print(cmd)
				subprocess.check_call(cmd, shell=True)

				cmd = 'rrdtool graph png/%s__1d.png --end now --start end-1d --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
				print(cmd)
				subprocess.check_call(cmd, shell=True)

				cmd = 'rrdtool graph png/%s__1w.png --end now --start end-1w --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
				print(cmd)
				subprocess.check_call(cmd, shell=True)

				cmd = 'rrdtool graph png/%s__1m.png --end now --start end-1M --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
				print(cmd)
				subprocess.check_call(cmd, shell=True)

				last_vals[k] = v
			#endwhile

			time.sleep(1)  # TODO: hard-coded shit
		#endwhile

		logging.info('thread exit')
	#enddef

	def quit(self):
		self._run = False
	#enddef
#endclass

# TODO: globals are shit!!!
alerts = load_alerts('alerts.conf')

def main():
	logging.basicConfig(level='DEBUG')

	thr = MyThread()
	thr.start()

	app.run(host='::', threaded=True, debug=True)

	thr.quit()
	thr.join()

	logging.info('exit')
#enddef

if __name__ == '__main__':
	sys.exit(main())
#endif
