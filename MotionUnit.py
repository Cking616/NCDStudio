# -*- coding: utf-8 -*-

"""
@version: 1.0
@license: Apache Licence 
@author:  kht,cking616
@contact: cking616@mail.ustc.edu.cn
@software: PyCharm Community Edition
@file: MotionUnit
@time: 2017\12\12 0012
"""


from abc import ABCMeta, abstractmethod


class MotionUnit(metaclass=ABCMeta):
    @abstractmethod
    def process_cmd(self, cmd, device_adapter):
        pass


class ScaraUnit(MotionUnit):
    def __init__(self, name):
        self.name = name
        self.is_correct = True

    def process_cmd(self, cmd, device_adapter):
        _send_len = device_adapter.send_message(self.name, cmd)
        if _send_len != len(cmd):
            return False
        _msg = device_adapter.receive_message(self.name)
        _flag = _msg[:7]
        if _flag != "!E END-":
            return False
        return True

    def get_current_position(self):
        pass

    def is_ready(self):
        return self.is_correct


class StepMotorUnit(MotionUnit):
    def __init__(self, name):
        self.name = name
        self.is_correct = True

    def process_cmd(self, cmd, device_adapter):
        _send_len = device_adapter.send_message(self.name, cmd)
        if _send_len != len(cmd):
            return False
        _msg = device_adapter.receive_message(self.name)
        _exp = cmd[1:]
        if _msg != _exp:
            return False
        return True

    def get_current_position(self):
        pass

    def is_ready(self):
        return self.is_correct


class WidReaderUnit(MotionUnit):
    def __init__(self, name):
        self.name = name
        self.is_correct = True
        self.widList = []

    def process_cmd(self, cmd, device_adapter):
        if cmd == 'read wid':
            wid = device_adapter.read_wafer_id()
            if wid:
                self.widList.append(wid)
                return True
        return False

    def is_ready(self):
        return self.is_correct

    def get_wafer_id(self):
        return self.widList.pop(0)


def create_motion_unit(name, unit_type):
    if unit_type == "SCARA":
        return ScaraUnit(name)
    if unit_type == "STEPMOTOR":
        return StepMotorUnit(name)
    if unit_type == "WIDREADER":
        return WidReaderUnit(name)


class UnitManager:
    def __init__(self, json_data, device_adapter):
        self.device = device_adapter
        self.unit_dict = {}
        self.is_correct = True
        motion_unit_data = json_data["MotionUnit"]
        num_of_motion_unit = motion_unit_data["numOfMotionUnit"]
        if num_of_motion_unit > 0:
            motion_unit_list = motion_unit_data["motionUnitList"]
            for i in range(num_of_motion_unit):
                unit_name = motion_unit_list[i]["name"]
                unit_type = motion_unit_list[i]["type"]
                motion_unit = create_motion_unit(unit_name, unit_type)
                if motion_unit.is_ready():
                    self.unit_dict[unit_name] = motion_unit

    def process(self, name, cmd):
        unit = self.unit_dict[name]
        if unit:
            return unit.process_cmd(cmd, self.device)
        return False

    def is_ready(self):
        return self.is_correct

    def get_wafer_id(self):
        return self.unit_dict['wid_reader'].get_wafer_id()


