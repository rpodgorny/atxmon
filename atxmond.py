#!/usr/bin/python3

import sys
import cherrypy


class AtxMonServer:
	def __init__(self):
		self.data = []
	#enddef

	@cherrypy.expose
	def index(self):
		return 'index'
	#enddef

	@cherrypy.expose
	def save(self, src, dst, datetime, key, value):
		p = (src, dst, datetime, key, value)
		self.data.append(p)
		return str(p)
	#enddef

	@cherrypy.expose
	def show(self):
		return str(self.data)
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
