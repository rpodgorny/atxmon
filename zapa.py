#!/usr/bin/python3

import logging
import pymongo
import jinja2


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

	x = []
	for mj, loc in zapa.items():
		logging.info('processing %s' % mj)

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
