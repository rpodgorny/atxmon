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
import json
import pymongo


HISTORY_LEN = 10
GEN_PNG = False

# TODO: globals are shit
app = flask.Flask(__name__)
db = pymongo.MongoClient().atxmon
data = []
data_last = {}
evts = []  # TODO: this is shitty name
last_vals = {}  # TODO: shitty name

# TODO: move this
db.data.ensure_index('k')
db.data.ensure_index('t')
#db.data.ensure_index(['k', 'v'])
#db.data.ensure_index(['k', 't'])
#db.data.ensure_index(['k', 'v', 't'])
db.changes.ensure_index('k')
db.changes.ensure_index('t')


# TODO: ugly name, ugly functionality
def normalize(s):
	return s.replace('/', '__').replace(' ', '_').replace(':', '_')
#enddef

def load_json(fn):
	with open(fn, 'r') as f:
		return json.load(f)
	#endwith
#enddef

def save_json(data, fn):
	with open(fn, 'w') as f:
		return json.dump(data, f, indent=2)
	#endwith
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

# TODO: factor this out - no connection to atxmon
def load_zapa(fn):
	ret = {}
	with open(fn, 'r') as f:
		for line in f:
			line = line.strip()
			if not line: continue
			mj, loc = line.split(' ', 1)
			mj = mj.lower()
			ret[mj] = loc
		#endfor
	#endwith
	return ret
#enddef

@app.route('/')
def index():
	return 'index'
#enddef

'''
# TODO: factor this out - no connection to atxmon
@app.route('/zapareport1')
def zapareport1():
	zapa = load_zapa('zapa.txt')

	x = []
	for mj, loc in zapa.items():
		query = {'k': {'$regex': '.*/ping6/%s\.asterix\.cz/ok' % mj}}
		#query = {'k': {'$regex': '.*%s.*' % mj}}
		for doc in db.changes.find(query).sort([('t', 1), ]):
		#for doc in db.changes.find(query):
			k = doc['k']
			v = doc['v']
			t = doc['t']
			x.append((mj, loc, k, v, t))
		#endfor
	#endfor

	return flask.render_template('zapareport1.html', data_last=x)
#enddef
'''

# TODO: factor this out - no connection to atxmon
@app.route('/zapareport1')
def zapareport1():
	zapa = load_zapa('zapa.txt')

	x = []
	for mj, loc in zapa.items():
		v_last = None
		t_last = None
		query = {'k': {'$regex': '.*/ping6/%s\.asterix\.cz/ok' % mj}}
		for doc in db.data.find(query).sort([('t', 1), ]):
			k = doc['k']
			v = doc['v']
			t = doc['t']

			if v != v_last:
				x.append((mj, loc, 'vyp/zap', v, t))
			elif not t_last or (t - t_last).total_seconds() > 3600:
				x.append((mj, loc, 'mezera', v, t))
			#endif

			v_last = v
			t_last = t
		#endfor
	#endfor

	return flask.render_template('zapareport1.html', data_last=x)
#enddef

@app.route('/save', methods=['GET', 'POST'])
def save_many():
	d = flask.request.get_json(force=True)
	print('will save %s entries' % len(d))

	data.extend(d)

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

@app.route('/events')
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
				print('data', k, v, t, interval)

				db.data.insert_one({'k': k, 'v': v, 't': datetime.datetime.fromtimestamp(t)})

				if not k in data_last: data_last[k] = []
				data_last[k].insert(0, (v, t))
				data_last[k] = data_last[k][:HISTORY_LEN]

				if v != last_vals.get(k):
					print('change', k, v, t, interval)
					db.changes.insert_one({'k': k, 'v': v, 't': datetime.datetime.fromtimestamp(t)})

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

				if GEN_PNG:
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
				#endif

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

	global data, data_last, evts, last_vals

	if os.path.isfile('state.json'):
		logging.info('loading state from state.json')
		s = load_json('state.json')
		data = s.get('data', data)
		data_last = s.get('data_last', data_last)
		evts = s.get('evts', evts)
		last_vals = s.get('last_vals', last_vals)
	#endif

	thr = MyThread()
	thr.start()

	app.run(host='::', threaded=True)

	thr.quit()
	thr.join()

	logging.info('saving state to state.json')
	s = {}
	s['data'] = data
	s['data_last'] = data_last
	s['evts'] = evts
	s['last_vals'] = last_vals
	save_json(s, 'state.json')

	logging.info('exit')
#enddef

if __name__ == '__main__':
	sys.exit(main())
#endif
