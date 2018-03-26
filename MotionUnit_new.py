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
import threading


class NanotecUnit:
    def __init__(self):
        self.cmdBuffer = []
        self.lastSend = None
        self.error = ""
        self.sendBuffer = []
        self.lock = threading.RLock()
        self.canSend = False

    def on_connect(self):
        self.lock.acquire()
        self.canSend = True
        self.lock.release()

    def on_close(self):
        self.lock.acquire()
        self.canSend = False
        self.lock.release()

    def on_read(self, rec):
        if rec == self.lastSend.encode('utf-8'):
            self.lock.acquire()
            # if self.lastSend != '1A\r':
            self.canSend = True
            if self.cmdBuffer:
                self.sendBuffer = self.cmdBuffer.pop()
                self.lastSend = self.sendBuffer
                self.sendBuffer = '#' + self.sendBuffer
            self.lock.release()
        else:
            if self.lastSend == '1A\r':
                self.canSend = True
            self.error = rec

    def writable(self):
        if self.error != "":
            return False
        if len(self.cmdBuffer) > 0:
            return True
        else:
            return len(self.sendBuffer) > 0

    def on_write(self, send_func):
        if not self.sendBuffer:
            return
        if not self.canSend:
            return
        sent = send_func(self.sendBuffer.encode('utf-8'))
        self.lock.acquire()
        self.sendBuffer = self.sendBuffer[sent:]
        self.lock.release()
        if not self.sendBuffer:
            self.lock.acquire()
            self.canSend = False
            self.lock.release()

    def is_error(self):
        return self.error != ""

    def exec_cmd(self, cmd):
        self.lock.acquire()
        self.cmdBuffer = cmd
        if self.cmdBuffer:
            self.sendBuffer = self.cmdBuffer.pop()
            self.lastSend = self.sendBuffer
            self.sendBuffer = '#' + self.sendBuffer
        self.canSend = True
        self.lock.release()

    def is_cmd_end(self):
        self.lock.acquire()
        can_send = self.canSend
        writable = self.writable()
        self.lock.release()
        return (not writable) and can_send


class TCPClient(asyncore.dispatcher):
    def __init__(self, host, unit):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect(host)
        self.unit = unit

    def handle_connect(self):
        self.unit.on_connect()

    def handle_close(self):
        self.unit.on_close()
        self.close()

    def handle_read(self):
        rec = self.recv(8192)
        self.unit.on_read(rec)

    def writable(self):
        return self.unit.writable()

    def handle_write(self):
        self.unit.on_write(self.send)


if __name__ == '__main__':
    import time
    xMotor = NanotecUnit()
    yMotor = NanotecUnit()
    # xMotor = NanotecMotor(('192.168.100.254', 4004))
    # yMotor = NanotecMotor(('192.168.100.254', 4001))

    cmdPro = ['1A\r',
              '1y1\r',
              '1:ramp_mode=2\r',
              '1J=1\r',
              '1:port_in_f=0\r',
              '1:port_in_e=7\r',
              '1:port_in_d=0\r',
              '1D\r',
              '1S\r']

    class MyThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)

        def run(self):
            TCPClient(('127.0.0.1', 6010), xMotor)
            asyncore.loop()

    t = MyThread()
    t.start()
    """
    yMotor.exec_cmd(cmdPro)
    while not yMotor.is_cmd_end():
        time.sleep(2)

    print("yMotor Home\n")

    cmdPro = ['1A\r',
              '1y1\r',
              '1:ramp_mode=2\r',
              '1J=1\r',
              '1:port_in_f=0\r',
              '1:port_in_e=7\r',
              '1:port_in_d=0\r',
              '1D\r',
              '1S\r']
    """
    xMotor.exec_cmd(cmdPro)
    while not xMotor.is_cmd_end():
        time.sleep(2)

    print("xMotor Home\n")
    input("Enter\n")
