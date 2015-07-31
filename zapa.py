#!/usr/bin/python3

import logging
import pymongo
import jinja2
import datetime


# TODO: globals are shit
db = pymongo.MongoClient().atxmon


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

def zapareport1():
	zapa = load_zapa('zapa.txt')

	#since = datetime.datetime(2014, 7, 30)
	since = datetime.datetime.now() - datetime.timedelta(hours=24)
	till = datetime.datetime.now()

	x = []
	for mj, loc in zapa.items():
		logging.info('processing %s' % mj)

		# just select the last one before since
		query = {'k': {'$regex': '.*/ping6/%s\.asterix\.cz/ok' % mj}, 't': {'$lt': since}}
		try:
			doc = db.data.find(query).sort([('t', -1), ])[0]
		except:
			doc = None
		#endtry

		if doc:
			state = doc['v']
			state_since = doc['t']
			t_last = doc['t']
		else:
			state = None
			state_since = since
			t_last = since
		#endif

		query = {'k': {'$regex': '.*/ping6/%s\.asterix\.cz/ok' % mj}, 't': {'$gte': since, '$lt': till}}
		for doc in db.data.find(query).sort([('t', 1), ]):
			k = doc['k']
			v = doc['v']
			t = doc['t']

			if v != state:
				if state is None:
					logging.debug('unk %s - %s' % (state_since, t))
					x.append((mj, loc, 'unk', v, state_since, t))
				elif state == 0:
					logging.debug('vyp %s - %s' % (state_since, t))
					x.append((mj, loc, 'vyp', v, state_since, t))
				#endif

				state = v
				state_since = t
			elif (t - t_last).total_seconds() > 3600:  # TODO: hard-coded shit
				if state is None:
					logging.debug('unk %s - %s' % (state_since, t))
					x.append((mj, loc, 'unk', v, state_since, t))
				elif state == 0:
					logging.debug('vyp %s - %s' % (state_since, t))
					x.append((mj, loc, 'vyp', v, state_since, t))
				#endif

				state = None
				state_since = t
			#endif

			t_last = t
		#endfor
	#endfor

	# TODO: the last record

	env = jinja2.Environment(loader=jinja2.PackageLoader('zapa', 'templates'))
	t = env.get_template('zapareport1.html')
	return t.render(data_last=x)
#enddef


def main():
	logging.basicConfig(level='DEBUG')

	with open('zapareport1_out.html', 'w') as f:
		f.write(zapareport1())
	#endwith
#enddef


if __name__ == '__main__':
	main()
#endif
