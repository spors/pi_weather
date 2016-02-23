import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import json
import time

data = {}

def parse_data(fname):
    
    with open(fname) as myfile:
        for line in myfile:
            name, var = line.partition("=")[::2]
            data[name.strip()] = float(var)

    return data


class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print('new connection')


        while True:
            data = parse_data('/home/pi/wxdata.txt')
            msg = json.dumps({'windSpeed': data['windSpeed'], 'windDir': data['windDir']})
            self.write_message(msg)

            time.sleep(1)

    def on_message(self, message):
        print('message received %s' % message)

    def on_close(self):
      print('connection closed')

application = tornado.web.Application([
    (r'/ws', WSHandler),
])


if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(9998)
    tornado.ioloop.IOLoop.instance().start()

