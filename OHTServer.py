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
rampState = 0


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
    elif receive[:6] == 'ERROR-':
        cmdError = True
        return True
    elif receive[-1] == '.':
        tmp_state = receive.split(',')[1]
        global rampState
        rampState = int(tmp_state)
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
    global isConnected
    global motorStatus
    global writeCMDBuffer
    while not isConnected:
        print("Wait for controller connect")
        time.sleep(1.5)
    writeCMDBuffer.append('P41')
    time.sleep(0.2)
    writeCMDBuffer.append('P4P460FE65537')
    time.sleep(0.2)
    writeCMDBuffer.append('P21')
    while not motorStatus:
        time.sleep(1)
        writeCMDBuffer.append('D')
        revCondition.acquire()
        ret = revCondition.wait(5)
        if not ret:
            writeCMDBuffer.append('D')
            ret = revCondition.wait()
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
        print("Wait for Motor init")


def scan_flags():
    global writeCMDBuffer
    global wheelEncoder
    global motorStatus
    global recCMD
    global gFlag
    writeCMDBuffer.append('E9')
    revCondition.acquire()
    ret = revCondition.wait(5)
    if not ret:
        writeCMDBuffer.append('E9')
        ret = revCondition.wait()
    if ret:
        wheel_encoder = recCMD
        wheelEncoder = wheel_encoder.split()[4]
        if wheelEncoder[-2] == '1':
            gFlag = 1
        else:
            gFlag = 0
    revCondition.release()

    while not gFlag:
        writeCMDBuffer.append('m9fg501000')
        time.sleep(0.5)
        writeCMDBuffer.append('E9')
        revCondition.acquire()
        ret = revCondition.wait(5)
        if not ret:
            writeCMDBuffer.append('E9')
            ret = revCondition.wait()
        if ret:
            wheel_encoder = recCMD
            wheelEncoder = wheel_encoder.split()[4]
            if wheelEncoder[-2] == '1':
                gFlag = 1
            else:
                gFlag = 0
        revCondition.release()
        time.sleep(0.2)
        print("Scanning")


def go_wheel_location(speed, flag, encoder):
    global gFlag
    if gFlag == 0:
        print("Flags Error, Reset Flag")
        return False

    global writeCMDBuffer
    global rampState
    if speed > 70:
        speed = 70
    if speed < 10:
        speed = 10

    cmd = 'r9lf%02d%d%d' % (speed, flag, encoder)
    writeCMDBuffer.append(cmd)
    rampState = 1
    time.sleep(1)
    while rampState:
        time.sleep(1)
        print("Doing")
    return True


def out_expand(mm):
    global writeCMDBuffer
    cur_encoder = 0
    writeCMDBuffer.append('P4G6064')
    revCondition.acquire()
    ret = revCondition.wait(5)
    if not ret:
        writeCMDBuffer.append('P4G6064')
        revCondition.wait()
        z_encoder = recCMD
        cur_encoder = int(z_encoder)
    revCondition.release()

    num = mm * 100
    target_p = cur_encoder - num
    _dir = 1
    while True:
        if _dir:
            cmd = "P4M-300"
        else:
            cmd = "P4M300"
        writeCMDBuffer.append(cmd)
        time.sleep(0.7)

        writeCMDBuffer.append('P4G6064')
        revCondition.acquire()
        ret = revCondition.wait(3)
        if not ret:
            writeCMDBuffer.append('P4G6064')
            revCondition.wait()
            z_encoder = recCMD
            cur_encoder = int(z_encoder)
        revCondition.release()

        err = target_p - cur_encoder
        if err > 0:
            _dir = 0
        else:
            _dir = 1
            err = -err
        if err < 400:
            break


def in_expand(mm):
    global writeCMDBuffer
    cur_encoder = 0
    writeCMDBuffer.append('P4G6064')
    revCondition.acquire()
    ret = revCondition.wait(5)
    if not ret:
        writeCMDBuffer.append('P4G6064')
        revCondition.wait()
        z_encoder = recCMD
        cur_encoder = int(z_encoder)
    revCondition.release()

    num = mm * 100
    target_p = cur_encoder + num
    _dir = 0
    while True:
        if _dir:
            cmd = "P4M-300"
        else:
            cmd = "P4M300"
        writeCMDBuffer.append(cmd)
        time.sleep(0.7)

        writeCMDBuffer.append('P4G6064')
        revCondition.acquire()
        ret = revCondition.wait(3)
        if not ret:
            writeCMDBuffer.append('P4G6064')
            revCondition.wait()
            z_encoder = recCMD
            cur_encoder = int(z_encoder)
        revCondition.release()

        err = target_p - cur_encoder
        if err > 0:
            _dir = 0
        else:
            _dir = 1
            err = -err
        if err < 400:
            break


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


def go_z_location(speed, encoder):
    global gFlag
    if gFlag == 0:
        print("Flags Error, Reset Flag")
        return False

    global writeCMDBuffer
    cmd = 'P2A%03d%d' % (speed, encoder)
    writeCMDBuffer.append('P2P460FE196609')
    time.sleep(0.5)
    writeCMDBuffer.append(cmd)
    time.sleep(0.2)
    while True:
        cur_encoder = 0
        writeCMDBuffer.append('P2G6064')
        revCondition.acquire()
        ret = revCondition.wait(5)
        if not ret:
            writeCMDBuffer.append('P2G6064')
            revCondition.wait()
            z_encoder = recCMD
            cur_encoder = int(z_encoder)
        revCondition.release()
        err = encoder - cur_encoder
        if -300 < err < 300:
            stop_z()
            break
        print("Doing, Err:%d" % err)
        writeCMDBuffer.append(cmd)
        time.sleep(0.5)
        writeCMDBuffer.append('P2P460FE196609')
        time.sleep(0.2)


def stop_wheel():
    writeCMDBuffer.append('r9tf000')
    time.sleep(0.3)
    writeCMDBuffer.append('m9fb72000')
    time.sleep(0.2)


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
