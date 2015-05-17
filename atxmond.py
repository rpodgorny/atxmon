#!/usr/bin/python3

import sys
import cherrypy


class AtxMonServer:
	def __init__(self):
		self.data = []
		self.data_last = {}
	#enddef

	@cherrypy.expose
	def index(self):
		return 'index'
	#enddef

	@cherrypy.expose
	def save(self, src, dst, datetime, test, result_name, result_value):
		p = (src, dst, datetime, test, result_name, result_value)
		self.data.append(p)
		self.data_last[(src, dst, test, result_name)] = (datetime, result_value)
		return str(p)
	#enddef

	@cherrypy.expose
	@cherrypy.tools.json_out()
	def show(self):
		return {'%s/%s/%s/%s' % (k[0], k[1], k[2], k[3]): v for k, v in self.data_last.items()}
	#enddef
#endclass

def main():
	cherrypy.server.socket_host = '0.0.0.0'
	cherrypy.server.socket_port = 8755

	s = AtxMonServer()
	cherrypy.quickstart(s)
#enddef

if __name__ == '__main__':
	sys.exit(main())
#endif
