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
        self.lock = threading.RLock()

    def handle_connect(self):
        self.lock.acquire()
        self.canSend = True
        self.lock.release()

    def handle_close(self):
        self.lock.acquire()
        self.canSend = False
        self.lock.release()
        self.close()

    def handle_read(self):
        rec = self.recv(8192)
        if rec == self.lastSend.encode('utf-8'):
            self.lock.acquire()
            if self.lastSend != '1A\r':
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

    def handle_write(self):
        if not self.sendBuffer:
            return
        if not self.canSend:
            return
        sent = self.send(self.sendBuffer.encode('utf-8'))
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


if __name__ == '__main__':
    import time

    # xMotor = NanotecMotor(('127.0.0.1', 6010))
    xMotor = NanotecMotor(('192.168.100.254', 4004))
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
            asyncore.loop()

    t = MyThread()
    t.start()
    time.sleep(2)

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
        time.sleep(1)

    print("xMotor Home\n")

    input("Enter\n")
