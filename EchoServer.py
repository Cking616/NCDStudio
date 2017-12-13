from socketserver import BaseRequestHandler, TCPServer


class EchoHandler(BaseRequestHandler):
    def handle(self):
        print('Got connection from', self.client_address)
        while True:
            msg = self.request.recv(8192)
            if not msg:
                break
            print(msg)
            msg = "!E END-"
            self.request.send(msg.encode('utf-8'))


if __name__ == '__main__':
    server = TCPServer(('127.0.0.1', 6000), EchoHandler)
    server.serve_forever()
