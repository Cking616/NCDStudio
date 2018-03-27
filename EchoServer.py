from socketserver import BaseRequestHandler, TCPServer


class EchoHandler(BaseRequestHandler):
    def handle(self):
        print('Got connection from', self.client_address)
        while True:
            msg = self.request.recv(8192)
            if not msg:
                break
            print(msg)
            if msg == 'HOME\n'.encode('utf-8'):
                self.request.send('!E END-HOME HOME\n'.encode('utf-8'))
            elif msg == 'WOB\n'.encode('utf-8'):
                self.request.send('!S WOB 7\n!E END-WOB 2 WOB\n'.encode('utf-8'))
            else:
                msg = msg[1:]
                self.request.send(msg)


if __name__ == '__main__':
    server = TCPServer(('127.0.0.1', 6010), EchoHandler)
    server.serve_forever()
