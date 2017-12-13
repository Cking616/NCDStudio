# -*- coding: utf-8 -*-

"""
@version: 1.0
@license: Apache Licence 
@author:  kht,cking616
@contact: cking616@mail.ustc.edu.cn
@software: PyCharm Community Edition
@file: TaskManager
@time: 2017\12\12 0012
"""


from DeviceAdapter import DeviceAdapter
from MotionUnit import UnitManager
import json


class TaskManager:
    def __init__(self, init_json_file):
        self.is_correct = False
        with open(init_json_file, 'r') as f:
            reads = f.read()
            json_data = json.loads(reads)
        self.device = DeviceAdapter(json_data)
        if self.device.is_ready():
            self.unit_manager = UnitManager(json_data, self.device)
            if self.unit_manager.is_ready():
                self.is_correct = True

    def process(self, process_json):
        return_value = True
        with open(process_json, 'r') as f:
            reads = f.read()
            json_data = json.loads(reads)
        process_cmd = json_data["processCMD"]
        for cmd in process_cmd:
            cmd_name = cmd["target"]
            cmd_cmd = cmd["cmd"]
            if not self.unit_manager.process(cmd_name, cmd_cmd):
                return_value = False
                break
        return return_value

    def is_ready(self):
        return self.is_correct

    def get_wafer_id(self):
        return self.unit_manager.get_wafer_id()


if __name__ == '__main__':
    taskManger = TaskManager('init.json')
    while True:
        name = input("Process json name\n")
        ret = taskManger.process(name)
        print(ret)
        wid = taskManger.get_wafer_id()
        wid = "WaferId is:" + wid
        print(wid)
