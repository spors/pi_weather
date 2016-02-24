import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import json

data = {}
clients = []

def parse_data(fname):
    
    with open(fname) as myfile:
        for line in myfile:
            name, var = line.partition("=")[::2]
            data[name.strip()] = float(var)

    return data


def send_data():
    for cl in clients:
        #data = parse_data('/home/pi/wxdata.txt')
        #msg = json.dumps({'windSpeed': data['windSpeed'], 'windDir': data['windDir']})
        msg = json.dumps({'windSpeed': 5, 'windDir': 180})
        cl.write_message(msg)


class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print('new connection')
        
        if self not in clients:
            clients.append(self)

    def on_message(self, message):
        print('message received %s' % message)

    def on_close(self):
      print('connection closed')
      
      if self in clients:
            clients.remove(self)
            
    def check_origin(self, origin):
        return True


application = tornado.web.Application([(r'/ws', WSHandler),])

http_server = tornado.httpserver.HTTPServer(application)
http_server.listen(9998)
tornado.ioloop.PeriodicCallback(send_data, 1000).start()
tornado.ioloop.IOLoop.instance().start()
