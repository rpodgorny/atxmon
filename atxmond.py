#!/usr/bin/python3

import sys
import flask
import json
import datetime

app = flask.Flask(__name__)
data = []
data_last = {}

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
	data.append(p)
	data_last[k] = (v, t)
	return str(p)
#enddef

@app.route('/save', methods=['GET', 'POST'])
def save_many():
	d = flask.request.get_json(force=True)
	print('will save %s entries' % len(d))

	data.extend(d)
	for k, v, t in d:
		data_last[k] = (v, t)
	#endfor
	return 'ok'
#enddef

@app.route('/show')
def show():
	x = []
	for k in sorted(data_last.keys()):
		v, t = data_last[k]
		t = datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')
		x.append((k, v, t))
	#endfor

	return flask.render_template('show.html', data_last=x)
#enddef

def main():
	app.run(host='::', threaded=True, debug=True)
#enddef

if __name__ == '__main__':
	sys.exit(main())
#endif
