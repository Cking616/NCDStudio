import time
import asyncore
import socket
import threading

recCMD = ""
writeCMD = ""
revCondition = threading.Condition()
isConnected = False
zEncoder = 0
wheelEncoder = 0
motorStatus = False
cmdError = False
gFlag = 0


class OhtHandler(asyncore.dispatcher_with_send):
    def handle_read(self):
        global recCMD
        global cmdError
        global gFlag
        revCondition.acquire()
        data = self.recv(1024)
        if data:
            tmp_rec = data.decode('utf-8')
            if tmp_rec[:3] == 'ERR':
                cmdError = True
            elif tmp_rec[:6] == 'Flags:':
                gFlag = 1
            else:
                recCMD = tmp_rec
                revCondition.notify()
        revCondition.release()

    def handle_close(self):
        global isConnected
        isConnected = False

    def writable(self):
        return True

    def handle_write(self):
        global writeCMD
        if not writeCMD:
            return
        self.send(writeCMD.encode('utf-8'))
        writeCMD = ""


class OhtServer(asyncore.dispatcher):
    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(5)
        self.handler = None

    def handle_accept(self):
        conn, address = self.accept()
        print('Incoming connection from %s' % repr(address))
        self.handler = OhtHandler(conn)
        global isConnected
        isConnected = True


class OhtServerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        server = OhtServer('192.168.0.181', 5000)
        asyncore.loop()


class _Timer(threading.Thread):
    def __init__(self, interval, func, args=[], kwargs={}):
        threading.Thread.__init__(self)
        self.interval = interval
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.finished = threading.Event()

    def cancel(self):
        self.finished.set()

    def run(self):
        self.finished.wait(self.interval)
        if not self.finished.is_set():
            self.func(*self.args, **self.kwargs)
        self.finished.set()


class LoopTimer(_Timer):
    def __init__(self, interval, func, args=[], kwargs={}):
        _Timer.__init__(self, interval, func, args, kwargs)

    def run(self):
        while True:
            if not self.finished.is_set():
                self.finished.wait(self.interval)
                self.func(*self.args, **self.kwargs)
            else:
                break


def timer_thread():
    if not isConnected:
        return

    global writeCMD
    global zEncoder
    global wheelEncoder
    global motorStatus
    writeCMD = 'E9'
    revCondition.acquire()
    revCondition.wait()
    wheel_encoder = recCMD
    wheelEncoder = wheel_encoder.split()[0]
    wheelEncoder = wheelEncoder[2:]
    wheelEncoder = int(wheelEncoder)
    revCondition.release()
    # print(wheelEncoder)
    # print('Wheel Encoder: %s' % wheel_encoder)

    writeCMD = 'P2G6064'
    revCondition.acquire()
    revCondition.wait()
    z_encoder = recCMD
    zEncoder = int(z_encoder)
    revCondition.release()
    print("z:%d" % zEncoder)
    # print('Z Encoder: %s' % z_encoder)

    writeCMD = 'D'
    revCondition.acquire()
    revCondition.wait()
    motor_status = recCMD
    if motor_status[:3] == '3ii':
        motorStatus = True
    else:
        motorStatus = False
    revCondition.release()
    # print(motorStatus)
    # print('Motor Status: %s' % motor_status)


def init_controller():
    global writeCMD
    writeCMD = 'P41'
    time.sleep(0.3)
    writeCMD = 'P4P460FE65537'
    time.sleep(0.3)
    writeCMD = 'P21'


def go_wheel_location(encoder):
    global wheelEncoder
    error_pos = wheelEncoder - encoder
    if error_pos > 0:
        direction = 0
    else:
        direction = 1
        error_pos = - error_pos

    global writeCMD

    if error_pos <= 300:
        writeCMD = 'm9fb72000'
        return True

    while True:
        if error_pos > 20000:
            pwd = 60
            run_time = 1000
        elif 10000 < error_pos <= 20000:
            pwd = 60
            run_time = 500
        elif 5000 < error_pos <= 10000:
            pwd = 50
            run_time = 500
        elif 1000 < error_pos <= 5000:
            pwd = 40
            run_time = 500
        else:
            pwd = 35
            run_time = 500
        if direction:
            cmd = 'm9fg%d%d' % (pwd, run_time)
        else:
            cmd = 'm9rg%d%d' % (pwd, run_time)

        writeCMD = cmd
        time.sleep(1.3)

        error_pos = wheelEncoder - encoder
        if error_pos > 0:
            direction = 0
        else:
            direction = 1
            error_pos = - error_pos

        if error_pos <= 1000:
            writeCMD = 'm9fb72000'
            return True


def out_expand(mm):
    num = mm * 100
    cmd = "P4M-%d" % num
    global writeCMD
    writeCMD = cmd
    time.sleep(10)


def in_expand(mm):
    num = mm * 100
    cmd = "P4M%d" % num
    global writeCMD
    writeCMD = cmd
    time.sleep(10)


def go_z_location(encoder):
    global zEncoder
    error_pos = zEncoder - encoder
    if error_pos > 0:
        direction = 0
    else:
        direction = 1
        error_pos = - error_pos

    global writeCMD

    if error_pos <= 200:
        writeCMD = 'P2P460FE1'
        time.sleep(0.2)
        writeCMD = 'P2P260407'
        return True

    if direction:
        cmd = 'P2V10'
    else:
        cmd = 'P2V-10'

    writeCMD = cmd
    time.sleep(0.7)
    writeCMD = 'P2P460FE196609'
    time.sleep(0.2)
    while True:
        error_pos = zEncoder - encoder
        if error_pos < 0:
            error_pos = - error_pos

        if error_pos <= 300:
            writeCMD = 'P2P460FE1'
            time.sleep(0.3)
            writeCMD = 'P2P260407'
            return True
        time.sleep(0.75)


def init_servers():
    OhtServerThread().start()
    time.sleep(1.5)
    timer_pro = LoopTimer(0.5, timer_thread)
    timer_pro.start()
    time.sleep(3)
