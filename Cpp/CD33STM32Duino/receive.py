#!python3
import datetime
import logging
import os
import struct
import time
from time import sleep

import serial

END = b'\xC0'
ESC = b'\xDB'
ESC_END = b'\xDC'
ESC_ESC = b'\xDD'


def parse(rx):
    # SLIP に基づいたデコード
    # https://qiita.com/hideakitai/items/347985528656be03b620#%E3%83%87%E3%82%B3%E3%83%BC%E3%83%89
    d = b''
    i = 0
    while i < len(rx):
        rdata = rx[i].to_bytes(1, 'big')
        if(rdata == END):
            pass
        elif(rdata == ESC):
            next = rx[i+1].to_bytes(1, 'big')
            if(next == ESC_END):
                d += END
            elif(next == ESC_ESC):
                d += ESC
            i = i + 1
        else:
            d += rdata
        i = i + 1
    return d


if __name__ == '__main__':
    """
        CD33STM32Duino.ino と連携してCD33の計測データを指定された秒数の間読み出す
    """

    dir = os.path.dirname(os.path.abspath(__file__))
    # logger
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename=dir+"/receive.log", level=logging.DEBUG,
                        format='[%(asctime)s] %(module)s.%(funcName)s \t%(levelname)s \t%(message)s')

    now = datetime.datetime.now()
    fs = open(dir+'/{:%Y%m%d-%H%M%S}_control.csv'.format(now), 'w')
    fs.write("us, mm\n")

    port = "COM9"
    device = serial.Serial(port)
    device.baudrate = 1000000
    device.parity = serial.PARITY_NONE
    device.bytesize = serial.EIGHTBITS
    device.stopbits = serial.STOPBITS_ONE
    device.timeout = 0.1  # sec
    device.reset_input_buffer()
    device.reset_output_buffer()

    # 測定秒数指定
    # "#10" -> 10秒読みだし
    device.write("#10\r".encode())

    sleep(1)
    # 測定開始
    device.write("S\r".encode())
    while(1):
        rx = device.read_until(END)
        try:
            raw = parse(rx)
            time, length = struct.unpack("Lf", raw)
            data = str(time) + ", " + '{:.4f}'.format(length)
            if(length >= 9999):
                # 測定データとして9999が来ることはないのでマイコン側で終了の合図としておく
                break
            print(data)
            fs.write(data + "\n")
        except Exception as e:
            logger.error(raw.hex() + e)
