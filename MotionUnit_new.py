# -*- coding: utf-8 -*-

"""
@version: 1.0
@license: Apache Licence
@author:  kht,cking616
@contact: cking616@mail.ustc.edu.cn
@software: PyCharm Community Edition
@file: MotionUnit_new
@time: 2018\03\26
"""

import asyncore
import socket


class NanotecMotor(asyncore.dispatcher):
    def __init__(self, host):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(host)
        self.cmdBuffer = []
        self.sendBuffer = []
        self.error = ""
        self.canSend = False
        self.lastSend = None

    def handle_connect(self):
        self.canSend = True

    def handle_close(self):
        self.canSend = False
        self.close()

    def handle_read(self):
        rec = self.recv(8192)
        if rec == self.lastSend:
            self.canSend = True
        else:
            self.error = rec

    def writable(self):
        if self.error != "":
            return False
        if len(self.cmdBuffer) > 0:
            return True
        else:
            return len(self.sendBuffer) > 0

    def handle_write(self):
        if not self.sendBuffer:
            return
        if not self.canSend:
            return
        sent = self.send(self.sendBuffer.encode('utf-8'))
        self.sendBuffer = self.sendBuffer[sent:]
        if not self.sendBuffer:
            self.sendBuffer = self.cmdBuffer.pop()
            self.sendBuffer = '#' + self.sendBuffer
            self.canSend = False

    def is_error(self):
        return self.error != ""

    def exec_cmd(self, cmd):
        self.cmdBuffer = cmd
        self.sendBuffer = self.cmdBuffer.pop()
        self.sendBuffer = '#' + self.sendBuffer
        self.canSend = False

    def is_cmd_end(self):
        return not self.writable()


if __name__ == '__main__':
    xMotor = NanotecMotor(('192.168.100.254', 4001))

    cmdPro = ['1A\r',
              '1y1\r',
              '1:ramp_mode=2\r',
              '1J=1\r',
              '1:port_in_f=0\r',
              '1:port_in_e=7\r',
              '1:port_in_d=0\r',
              '1:D\r',
              '1S\r']

    asyncore.loop()
