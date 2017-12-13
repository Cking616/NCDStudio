# -*- coding: utf-8 -*-

"""
@version: 1.0
@license: Apache Licence 
@author:  kht,cking616
@contact: cking616@mail.ustc.edu.cn
@software: PyCharm Community Edition
@file: DeviceAdapter
@time: 2017/12/12
"""


import socket
import cffi
import os
import serial


class DeviceAdapter:
    def __init__(self, json_data):
        self.ffi = cffi.FFI()
        self.tcp_client_dict = {}
        self.serial_dict = {}
        self.wid_manager = None
        self.is_correct = True
        init_data = json_data
        device_adapter_data = init_data['DeviceAdapter']

        # Tcp clients initialization
        tcp_client = device_adapter_data['tcpClient']
        num_of_tcp_client = tcp_client['numOfTcpClient']
        if num_of_tcp_client > 0:
            tcp_client_data = tcp_client['tcpClientList']
            for i in range(num_of_tcp_client):
                tcp_address = tcp_client_data[i]['address']
                tcp_port = tcp_client_data[i]['port']
                tcp_name = tcp_client_data[i]['name']
                tcp_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ret = tcp_client.connect_ex((tcp_address, tcp_port))
                if ret == 0:
                    self.tcp_client_dict[tcp_name] = tcp_client

        # Serial initialization
        serial_data = device_adapter_data['serial']
        num_of_serial = serial_data['numOfSerial']
        if num_of_serial > 0:
            serial_list_data = serial_data['serialList']
            for i in range(num_of_serial):
                serial_port = serial_list_data[i]['port']
                serial_baud = serial_list_data[i]['baud']
                serial_name = serial_list_data[i]['name']
                tmp_serial = serial.Serial(port=serial_port, baudrate=serial_baud,
                                           bytesize=8, parity='E', stopbits=1, timeout=2)
                if tmp_serial:
                    self.serial_dict[serial_name] = tmp_serial

        # Wid manager initialization
        self.ffi.cdef("""
void *  FuncCreateDll();
int     FuncDestroyDll(           void * objptr);
int     FuncInit(                 void * objptr, char *cpIPAddress);
int     FuncIsInitialized(        void * objptr);
int     FuncGetVersionParam(      void * objptr, char *cVersion, int nMaxLen);
int     FuncGetVersion(           void * objptr, char *cVersion, int nMaxLen);
int     FuncSwitchOverlay(        void * objptr, int bOnOff);
int     FuncExit(                 void * objptr);
int     FuncLiveGetImage(         void * objptr, const char *cpFileName, int nChannel, int nIntensity, int nColor);
int     FuncLiveRead(             void * objptr);
int     FuncLiveGetImageRead(     void * objptr, const char *cpFileName, int nChannel, int nIntensity, int nColor );
int     FuncProcessRead(          void * objptr);
int     FuncProcessGetImage(      void * objptr, const char *cpFileName, int nTypeImage);
int     FuncGetWaferId(           void * objptr, char * cReadId, int nMaxLen, int *bReadSuccessful);
int     FuncGetCodeQualityOCR(    void * objptr, int *pnQuality);
int     FuncGetCodeQualityBCR(    void * objptr, int *pnQuality);
int     FuncGetCodeQualityDMR(    void * objptr, int *pnQuality);
int     FuncGetCodeQualityLast(   void * objptr, int *pnQuality);
int     FuncGetCodeTime(          void * objptr, int *pnTime);
int     FuncLoadRecipes(          void * objptr, const char *cpFilePath, const char *cpFilename);
int     FuncLoadRecipesToSlot(    void * objptr, const char *cpFilePath, const char *cpFilename, int nSlot);
int     FuncGetLastError(         void * objptr);
int     FuncGetErrorDescription(  void * objptr, int nError, char* strText, int nTextLength);
        """)
        _file = 'wid110Lib.dll'
        _path = os.path.join(*(os.path.split(__file__)[:-1] + (_file,)))
        self.wid_lib = self.ffi.dlopen(_path)
        self.wid_manager = self.wid_lib.FuncCreateDll()
        self.is_wid_manager_init = False
        wid_manager_data = device_adapter_data["widManager"]
        is_wid_manager_open = wid_manager_data['isOpen']
        if is_wid_manager_open:
            wid_address = wid_manager_data['address']
            self.wid_lib.FuncInit(self.wid_manager, wid_address)
            self.is_wid_manager_init = self.wid_lib.FuncIsInitialized(self.wid_manager)

    def __exit__(self):
        for key in self.tcp_client_dict.keys():
            self.tcp_client_dict[key].close()

        if self.wid_manager:
            self.wid_lib.FuncDestroyDll(self.wid_manager)

    def send_message(self, _name, _msg):
        if _name in self.tcp_client_dict.keys():
            _client = self.tcp_client_dict[_name]
            _ret = _client.send(_msg.encode('utf-8'))
            return _ret
        elif _name in self.serial_dict.keys():
            _serial = self.serial_dict[_name]
            _ret = _serial.write(_msg.encode('uft-8'))
            return _ret
        else:
            return 0

    def receive_message(self, _name):
        if _name in self.tcp_client_dict.keys():
            _client = self.tcp_client_dict[_name]
            _msg = _client.recv(8192)
            _msg = _msg.decode('utf-8')
            return _msg
        elif _name in self.serial_dict.keys():
            _msg = self.serial_dict[_name].readline()
            return _msg
        else:
            return None

    def read_water_id(self):
        if not self.is_wid_manager_init:
            return None
        self.wid_lib.FuncProcessRead(self.wid_manager)
        tmp_char = self.ffi.new('char []', "123456789012345")
        ret_result = self.ffi.new('int *')
        self.wid_lib.FuncGetWaterId(self.wid_manager, tmp_char, 16, ret_result)
        water_id = self.ffi.string(tmp_char)
        return water_id

    def is_ready(self):
        return self.is_correct


if __name__ == '__main__':
    deviceAdapter = DeviceAdapter('init.json')
    while True:
        name = input("请输入发生的对象\n")
        msg = input("请输入发送的内容\n")
        deviceAdapter.send_message(name, msg)
        rev = deviceAdapter.receive_message(name)
        print(rev)
