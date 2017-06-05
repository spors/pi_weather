#!/usr/bin/env python3

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import json

data = {}
clients = []

def Hg2Pa(pressure):
  # convert pressure from Hg to Pascal
  return(pressure / 0.000295299830714)

def F2C(temperature):
  # convert temperature from degrees Celsius to Fahrenheit
  return((temperature - 32) *  5/9)

def mph2mps(speed):
  # convert speed from miles per hour to meters per second
  return(speed / 2.23694)

def mph2kt(speed):
  # convert speed from miles per hour to knots
  return(speed * 0.868976)



def parse_data(fname):
    
    with open(fname) as myfile:
        for line in myfile:
            name, var = line.partition("=")[::2]
            data[name.strip()] = float(var)

    return data


def send_data():
    for cl in clients:
        data = parse_data('/home/wetterd/wxdata.txt')
        msg = json.dumps({'windSpeed': mph2kt(data['windSpeed']), 'windDir': data['windDir'], 'pressure': Hg2Pa(data['pressure']/100), 'inTemp': F2C(data['inTemp'])})
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
