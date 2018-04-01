# -*- coding: utf-8 -*-

"""
@version: 1.0
@license: Apache Licence 
@author:  kht,cking616
@contact: cking616@mail.ustc.edu.cn
@software: PyCharm Community Edition
@file: main
@time: 2018/4/1
"""
from OHTServer import *


def main_thread():
    init_controller()
    """
    go_wheel_location(0)
    time.sleep(2)
    go_wheel_location(-50000)
    time.sleep(2)
    go_wheel_location(50000)
    """
    # out_expand(860)
    # time.sleep(5)

    go_z_location(4000)
    time.sleep(5)
    go_z_location(200)

    time.sleep(5)
    in_expand(860)

    # go_wheel_location(0)
    return True


if __name__ == '__main__':
    init_servers()

    main_thread()
    import sys
    sys.exit(0)
