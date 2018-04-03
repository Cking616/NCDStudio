import time
import asyncore
import socket
import threading
import ctypes
import inspect

recCMD = ""
writeCMDBuffer = []
revCondition = threading.Condition()
isConnected = False
zEncoder = 0
wheelEncoder = 0
motorStatus = False
cmdError = False
gFlag = 0
isEndTimer = False


def parser_receive(receive):
    global gFlag
    global cmdError
    if receive[:9] == 'ERR Flags':
        gFlag = 0
        return True
    elif receive[:6] == 'Flags:':
        cmd = receive.split()
        dn = cmd[2]
        gFlag = int(dn[-2])
        return True
    elif receive == 'ERROR-CMD':
        cmdError = True
        return True
    elif receive[-1] == '.':
        return True
    else:
        return False


class OhtHandler(asyncore.dispatcher_with_send):
    def handle_read(self):
        global recCMD
        global cmdError
        global gFlag
        revCondition.acquire()
        data = self.recv(1024)
        if data:
            recCMD = ""
            tmp_rec = data.decode('utf-8')
            if not parser_receive(tmp_rec):
                recCMD = tmp_rec
                revCondition.notify()
        revCondition.release()

    def handle_close(self):
        global isConnected
        isConnected = False

    def writable(self):
        return True

    def handle_write(self):
        global writeCMDBuffer
        if not writeCMDBuffer:
            return
        cmd = writeCMDBuffer.pop(0)
        self.send(cmd.encode('utf-8'))
        while writeCMDBuffer:
            cmd = writeCMDBuffer.pop(0)
            self.send(cmd.encode('utf-8'))


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
    def __init__(self, address, port):
        threading.Thread.__init__(self)
        self.address = address
        self.port = port

    def run(self):
        server = OhtServer(self.address, self.port)
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
    global isConnected
    global isEndTimer
    if isEndTimer:
        return
    if not isConnected:
        return

    global writeCMDBuffer
    global zEncoder
    global wheelEncoder
    global motorStatus
    global recCMD
    writeCMDBuffer.append('E9')
    revCondition.acquire()
    ret = revCondition.wait(5)
    if not ret:
        writeCMDBuffer.append('E9')
        ret = revCondition.wait(5)
    if ret:
        wheel_encoder = recCMD
        wheelEncoder = wheel_encoder.split()[0]
        if wheelEncoder[1] == ':':
            wheelEncoder = wheelEncoder[2:]
            wheelEncoder = int(wheelEncoder)
    revCondition.release()
    # print(wheelEncoder)
    # print('Wheel Encoder: %s' % wheel_encoder)

    writeCMDBuffer.append('P2G6064')
    revCondition.acquire()
    ret = revCondition.wait(5)
    if not ret:
        writeCMDBuffer.append('P2G6064')
        ret = revCondition.wait(5)
    if ret:
        if len(recCMD) < 2 or recCMD[1] != ':':
            z_encoder = recCMD
            zEncoder = int(z_encoder)
    revCondition.release()
    # print("z:%d" % zEncoder)
    # print('Z Encoder: %s' % z_encoder)

    writeCMDBuffer.append('D')
    revCondition.acquire()
    ret = revCondition.wait(5)
    if not ret:
        writeCMDBuffer.append('D')
        ret = revCondition.wait(5)
    if ret:
        if recCMD[3] == ',':
            motor_status = recCMD
            if motor_status[:3] == '3ii':
                motorStatus = True
            elif motor_status[:3] == '3di':
                motorStatus = True
            else:
                motorStatus = False
    revCondition.release()
    # print(motorStatus)
    # print('Motor Status: %s' % motor_status)


def init_controller():
    global motorStatus
    while not motorStatus:
        time.sleep(1)
        print("Wait for Motor init")
    global writeCMDBuffer
    writeCMDBuffer.append('P41')
    time.sleep(0.2)
    writeCMDBuffer.append('P4P460FE65537')
    time.sleep(0.2)
    writeCMDBuffer.append('P21')
    time.sleep(2)
    print("Motor initialized")


def go_wheel_location(flag, encoder):
    global gFlag
    if gFlag == 0:
        print("Flags Error, Reset Flag")
        return False

    global writeCMDBuffer

    while True:
        if error_pos > 20000:
            pwd = 45
            run_time = 1000
        elif 10000 < error_pos <= 20000:
            pwd = 40
            run_time = 500
        elif 5000 < error_pos <= 10000:
            pwd = 30
            run_time = 500
        elif 1000 < error_pos <= 5000:
            pwd = 25
            run_time = 500
        else:
            pwd = 25
            run_time = 300
        if direction:
            cmd = 'm9fg%d%d' % (pwd, run_time)
        else:
            cmd = 'm9rg%d%d' % (pwd, run_time)

        writeCMDBuffer.append(cmd)
        time.sleep(0.75)

        error_pos = wheelEncoder - encoder
        if error_pos > 0:
            direction = 0
        else:
            direction = 1
            error_pos = - error_pos

        # print('Err: %d' % error_pos)
        if error_pos <= 700:
            writeCMDBuffer.append('m9fb72000')
            return True


def out_expand(mm):
    num = mm * 100
    cmd = "P4M-%d" % num
    global writeCMDBuffer
    writeCMDBuffer.append(cmd)
    time.sleep(0.5)
    writeCMDBuffer.append(cmd)
    time.sleep(10)


def in_expand(mm):
    num = mm * 100
    cmd = "P4M%d" % num
    global writeCMDBuffer
    writeCMDBuffer.append(cmd)
    time.sleep(0.5)
    writeCMDBuffer.append(cmd)
    time.sleep(10)


def grip():
    cmd = 'm630t3700'
    global writeCMDBuffer
    writeCMDBuffer.append(cmd)
    time.sleep(0.5)
    writeCMDBuffer.append(cmd)
    time.sleep(5)


def release():
    cmd = 'm631t3700'
    global writeCMDBuffer
    writeCMDBuffer.append(cmd)
    time.sleep(0.5)
    writeCMDBuffer.append(cmd)
    time.sleep(5)


def go_z_location(encoder):
    global zEncoder
    error_pos = zEncoder - encoder
    if error_pos > 0:
        direction = 0
    else:
        direction = 1
        error_pos = - error_pos

    global writeCMDBuffer

    if error_pos <= 200:
        writeCMDBuffer.append('P2P460FE1')
        time.sleep(0.2)
        writeCMDBuffer.append('P2P260407')
        return True

    if direction:
        cmd = 'P2V10'
    else:
        cmd = 'P2V-10'

    while writeCMDBuffer:
        time.sleep(0.1)
    writeCMDBuffer.append(cmd)
    time.sleep(0.7)
    writeCMDBuffer.append('P2P460FE196609')
    time.sleep(0.2)
    while True:
        error_pos = zEncoder - encoder
        if error_pos > 0:
            direction = 0
        else:
            direction = 1
            error_pos = - error_pos

        if direction:
            cmd = 'P2V10'
        else:
            cmd = 'P2V-10'
        # print('Err: %d' % error_pos)
        if error_pos <= 500:
            writeCMDBuffer.append('P2P460FE1')
            time.sleep(0.5)
            writeCMDBuffer.append('P2P260407')
            time.sleep(0.5)
            writeCMDBuffer.append('P2P460FE1')
            time.sleep(0.5)
            writeCMDBuffer.append('P2P260407')
            time.sleep(0.5)
            writeCMDBuffer.append('P2P460FE1')
            time.sleep(0.5)
            writeCMDBuffer.append('P2P260407')
            return True
        else:
            time.sleep(0.2)
            writeCMDBuffer.append(cmd)
            time.sleep(0.2)
            writeCMDBuffer.append('P2P460FE196609')
        time.sleep(0.5)


def stop_z():
    writeCMDBuffer.append('P2P460FE1')
    time.sleep(0.2)
    writeCMDBuffer.append('P2P260407')
    time.sleep(0.3)


def _async_raise(tid, exc_type):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exc_type):
        exc_type = type(exc_type)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exc_type))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)
