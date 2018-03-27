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
import re
import asyncore
import socket
import threading

from abc import ABCMeta, abstractmethod


class MotionUnit(metaclass=ABCMeta):
    @abstractmethod
    def on_connect(self):
        pass

    @abstractmethod
    def on_close(self):
        pass

    @abstractmethod
    def on_read(self, rec):
        pass

    @abstractmethod
    def writable(self):
        pass

    @abstractmethod
    def on_write(self, send_func):
        pass


"""
Nanotecs
"""


class NanotecUnit(MotionUnit):
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
        return True

    def __writable__(self):
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
        writable = self.__writable__()
        self.lock.release()
        return (not writable) and can_send


motor_home_cmd = ['1A\r',
                  '1y1\r',
                  '1:ramp_mode=2\r',
                  '1J=1\r',
                  '1:port_in_f=0\r',
                  '1:port_in_e=7\r',
                  '1:port_in_d=0\r',
                  '1D\r',
                  '1S\r']


xmotor_after_home_cmd = ['1A\r', '1o=600\r', '1y2\r', '1:port_in_f=8\r', '1:port_in_e=0\r', '1:ramp_mode=0\r']


"""
Robot
"""


class RobotUnit(MotionUnit):
    def __init__(self):
        self.error = ""
        self.sendBuffer = []
        self.lastSend = ""
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
        rec_str = rec.decode('utf-8')
        print(rec_str)
        lines = re.split(r'\n', rec_str)
        for line in lines:
            if line[:7] == '!E END-':
                self.canSend = True
            elif line[:8] == '!E ERROR':
                self.canSend = True
                self.error = line

    def writable(self):
        return True

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
        self.sendBuffer = cmd
        self.lastSend = cmd
        self.canSend = True
        self.lock.release()

    def is_cmd_end(self):
        self.lock.acquire()
        can_send = self.canSend
        cmd = self.sendBuffer
        self.lock.release()
        return can_send and (not cmd)


robot_home_cmd = 'HOME\n'
robot_wob_cmd = 'WOB\n'

"""
TCPClient
"""


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
    robot = RobotUnit()
    # xMotor = NanotecMotor(('192.168.100.254', 4004))
    # yMotor = NanotecMotor(('192.168.100.254', 4001))

    class MyThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)

        def run(self):
            TCPClient(('127.0.0.1', 6010), robot)
            # TCPClient(('127.0.0.1', 6010), xMotor)
            asyncore.loop()

    t = MyThread()
    t.start()

    tmp_cmd = robot_wob_cmd
    robot.exec_cmd(tmp_cmd)
    while not robot.is_cmd_end():
        time.sleep(2)

    print("robot_wob_cmd\n")

    tmp_cmd = robot_home_cmd
    robot.exec_cmd(tmp_cmd)
    while not robot.is_cmd_end():
        time.sleep(2)

    print("robot Home\n")
    """
    tmp_cmd = motor_home_cmd.copy()
    xMotor.exec_cmd(tmp_cmd)
    while not xMotor.is_cmd_end():
        time.sleep(2)

    print("xMotor Home\n")

    tmp_cmd = xmotor_after_home_cmd.copy()
    xMotor.exec_cmd(tmp_cmd)
    while not xMotor.is_cmd_end():
        time.sleep(2)

    print("xMotor Home\n")
    """
    input("Enter\n")
