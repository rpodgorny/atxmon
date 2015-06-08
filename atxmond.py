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


HISTORY_LEN = 10

# TODO: globals are shit
app = flask.Flask(__name__)
data = []
data_last = {}


# TODO: ugly name, ugly functionality
def normalize(s):
	return s.replace('/', '__').replace(' ', '_').replace(':', '_')
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

	for k, v, t in d:
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
		threading.Thread.__init__(self)

		self._run = True
	#enddef

	def run(self):
		logging.info('thread run')

		while self._run:
			while data:
				k, v, t = data.pop(0)
				print(k, v, t)

				fn = normalize(k)

				if not os.path.isfile('rrd/%s.rrd' % fn):
					cmd = 'rrdtool create rrd/%s.rrd --start 0 --step 1s DS:xxx:GAUGE:2s:U:U RRA:AVERAGE:0.999:1m:1h RRA:AVERAGE:0.999:1h:1d RRA:AVERAGE:0.999:1d:1M' % (fn, )
					print(cmd)
					subprocess.check_call(cmd, shell=True)
				#endif

				cmd = 'rrdtool update rrd/%s.rrd %d:%s' % (fn, int(t - 1), v)
				print(cmd)
				subprocess.check_call(cmd, shell=True)

				cmd = 'rrdtool update rrd/%s.rrd %d:%s' % (fn, int(t), v)
				print(cmd)
				subprocess.check_call(cmd, shell=True)

				cmd = 'rrdtool graph png/%s.png --end now --start end-10m --units-exponent 0 DEF:xxx=rrd/%s.rrd:xxx:AVERAGE LINE2:xxx#FF0000' % (fn, fn, )
				print(cmd)
				subprocess.check_call(cmd, shell=True)
			#endwhile

			time.sleep(1)  # TODO: hard-coded shit
		#endwhile

		logging.info('thread exit')
	#enddef

	def quit(self):
		self._run = False
	#enddef
#endclass

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
