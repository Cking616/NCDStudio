from socketserver import BaseRequestHandler, TCPServer


class EchoHandler(BaseRequestHandler):
    def handle(self):
        print('Got connection from', self.client_address)
        while True:
            msg = self.request.recv(8192)
            if not msg:
                break
            print(msg)
            msg = msg[1:]
            self.request.send(msg)


if __name__ == '__main__':
    server = TCPServer(('127.0.0.1', 6010), EchoHandler)
    server.serve_forever()
