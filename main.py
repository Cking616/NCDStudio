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
import OHTServer as Oht
import time
import threading

# 轮子使用速度，理论(0~79),实测低于40会有卡住的情况
# 高于60较危险，故这个脚本中统一取45
wheel_speed = 60

# 定义x轴三个点
# 1 号点定义参考以0号flag为参考，坐标偏差-200个编码器单位
wheel_point1_flag = 1
wheel_point1_encoder = 8200
# 2 号点定义参考以1号flag为参考，坐标偏差100个编码器单位
wheel_point2_flag = 1
wheel_point2_encoder = 38600
# 3 号点定义参考以2号flag为参考，坐标偏差100个编码器单位
wheel_point3_flag = 2
wheel_point3_encoder = 15000

# 定义Z轴两个点
# 由于Z轴定位偏差实测至少有300个编码器单位，故取高位点为300
# Z轴向下为正，且为相对编码器取每次上电时的坐标为坐标0点，故为了计算方便定义一个相对坐标0点
# X轴做扫描后会自动按Flag处理坐标0点，故不用做相关处理
zZero = 0
zPoint1 = zZero + 5000
zPoint2 = zZero - 500
zPoint3 = zZero + 6500
# 目前取Z速度为20，范围为（0~200）
zSpeed = 50

# 定义Y行程，860mm为完全伸出
YPoint = 860

# 定义地址，目前固件代码默认地址为 192.168.0.181
# port定义默认为5000
address = '192.168.0.181'
port = 5000


def pick(wf, we, zd):
    print("Wheel go to wheelPoint")
    Oht.go_wheel_location(wheel_speed, wf, we)
    print("Done")

    time.sleep(0.6)

    print("Out expand")
    Oht.out_expand(450, YPoint)
    print("Done")

    time.sleep(0.6)

    print("Z go to zPoint1")
    Oht.go_z_location(zSpeed, zd)
    print("Done")

    time.sleep(0.6)

    print("Grip")
    Oht.grip()
    print("Done")

    time.sleep(0.6)
    print("Z go to zPoint2")
    Oht.go_z_location(zSpeed, zPoint2)
    print("Done")

    time.sleep(0.6)
    print("In expand")
    Oht.in_expand(450, YPoint)
    print("Done")


def place(wf, we, zd):
    print("Wheel go to wheelPoint")
    Oht.go_wheel_location(wheel_speed, wf, we)
    print("Done")

    time.sleep(0.6)

    print("Out expand")
    Oht.out_expand(450, YPoint)
    print("Done")

    time.sleep(0.6)

    print("Z go to zPoint1")
    Oht.go_z_location(zSpeed, zd)
    print("Done")

    time.sleep(0.6)
    print("Release")
    Oht.release()
    print("Done")

    time.sleep(0.6)
    print("Z go to zPoint2")
    Oht.go_z_location(zSpeed, zPoint2)
    print("Done")

    time.sleep(0.6)
    print("In expand")
    Oht.in_expand(450, YPoint)
    print("Done")


def main_thread():
    Oht.init_controller()
    print("Motor initialized")

    # 目前要做定位运动，必须首先要对轨道flag扫描一圈且轨道安装的flag必须为3个（暂时未修改）
    print("Scan flags")
    Oht.scan_flags()
    print("Done")
    time.sleep(1)

    while True:
        print("Go wheel Point3")
        Oht.go_wheel_location(wheel_speed, wheel_point3_flag, wheel_point3_encoder)
        print("Done")
        time.sleep(0.6)
        pick(wheel_point2_flag, wheel_point2_encoder, zPoint3)
        time.sleep(0.6)
        print("Go wheel Point3")
        Oht.go_wheel_location(wheel_speed, wheel_point3_flag, wheel_point3_encoder)
        print("Done")
        time.sleep(0.6)
        place(wheel_point1_flag, wheel_point1_encoder, zPoint1)
        time.sleep(0.6)
        print("Go wheel Point3")
        Oht.go_wheel_location(wheel_speed, wheel_point3_flag, wheel_point3_encoder)
        print("Done")
        time.sleep(0.6)
        pick(wheel_point1_flag, wheel_point1_encoder, zPoint1)
        time.sleep(0.6)
        print("Go wheel Point3")
        Oht.go_wheel_location(wheel_speed, wheel_point3_flag, wheel_point3_encoder)
        print("Done")
        time.sleep(0.6)
        place(wheel_point2_flag, wheel_point2_encoder, zPoint3)
        time.sleep(0.6)


if __name__ == '__main__':
    server = Oht.OhtServerThread(address, port)
    server.start()
    time.sleep(1.5)

    main_pro = threading.Thread(target=main_thread)
    main_pro.start()
    input("输入Enter立即停止并退出\n")
    if main_pro.is_alive():
        Oht.stop_thread(main_pro)
    Oht.writeCMDBuffer = []
    Oht.stop_z()
    Oht.stop_wheel()
    import os
    os._exit(1)
