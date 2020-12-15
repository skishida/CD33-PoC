#!python3
import os
import serial
import logging
import time
from time import sleep

""" CD33

"""


class CD33:
    STX = b'\x02'
    ETX = b'\x03'

    # read value
    START_MEASURE = b'START_MEASURE'
    STOP_MEASURE = b'STOP_MEASURE'
    STOP_MEASURE_S = b'STOP_MEASURE_S'

    # q2 config
    STOP_Q2 = b'STOP_Q2'

    # avg config
    MODE_AVG_READ = b'AVG'
    MODE_AVG_FAST = b'AVG FAST'
    MODE_AVG_MID = b'AVG MEDIUM'
    MODE_AVG_SLOW = b'AVG SLOW'

    # mf config

    # error config

    # ext

    # other

    SERIAL_NO = b'SERIAL_NO'

    serial_number = ''

    def __init__(self, port):
        dir = os.path.dirname(os.path.abspath(__file__))
        # logger
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(filename=dir+"/cd33command.log", level=logging.DEBUG,
                            format='[%(asctime)s] %(module)s.%(funcName)s \t%(levelname)s \t%(message)s')

        # serialport
        self._serial = serial.Serial(port)
        self._serial.baudrate = 115200
        self._serial.parity = serial.PARITY_NONE
        self._serial.bytesize = serial.EIGHTBITS
        self._serial.stopbits = serial.STOPBITS_ONE
        self._serial.timeout = 0.1  # sec

        # check communincation
        self.send_command(self.STOP_MEASURE)
        self.send_command(self.STOP_MEASURE_S)
        self.send_command(self.STOP_Q2)
        rx = self._serial.readline()
        self._serial.reset_input_buffer()

        self.serial_number = self.send_command(self.SERIAL_NO, False)
        self.logger.info('CD33 Serial NO:' + str(self.serial_number))

    def send_command(self, command, is_response_bool=True, except_response=True):
        """[summary]

        Parameters
        ----------
        command : string
            [description]

        is_response_bool : bool, optional
            コマンドの応答がBoolで表せるか．
            設定読み出し等はFalse指定．デフォルト:True

        except_response : bool, optional
            コマンドに対して即時レスポンスを求めるか否か．
            連続読み出し等はFalse指定．デフォルト:True

        Returns
        -------
        [type]
            [description]
        """
        packet = self.STX
        packet += command
        packet += self.ETX
        self.logger.debug('TX> ' + str(packet))
        self._serial.write(packet)
        self._serial.flush()
        if except_response:
            return self.read_response(is_response_bool)
        return 1

    def read_response(self, is_response_bool=False):
        """[summary]

        Parameters
        ----------
        is_response_bool : bool, optional
            [description], by default False

        Returns
        -------
        [type]
            [description]
        """
        rx = self._serial.readline()
        stx = rx[0].to_bytes(1, 'big')
        etx = rx[-1].to_bytes(1, 'big')
        if(stx == self.STX and etx == self.ETX):
            self.logger.debug('RX< ' + str(rx))
            if(is_response_bool):
                if(rx[1].to_bytes(1, 'big') == b'\x3e'):
                    self.logger.info('command accepted')
                    return True
                elif(rx[1].to_bytes(1, 'big') == b'\x3f'):
                    self.logger.info('command rejected')
                    return False
                else:
                    pass
            ret = rx[1:]
            ret = ret[:-1]
            self.logger.debug(ret)
            return ret.decode()
        else:
            self.logger.warning('STX or ETX mismatch:' + str(rx))
            return False

    def read_val_continue(self):
        rx = self._serial.read_until(b'\x0d')
        return rx[:-1].decode()

    def read_val_continue_t(self):
        rx = self._serial.read_until(b'\x0d')
        return rx[:-1].decode(), time.perf_counter()

    def start_measure_continuous(self):
        self.send_command(self.START_MEASURE, False, False)
        self._serial.reset_input_buffer()

    def stop_measure(self):
        return self.send_command(self.STOP_MEASURE)

    def clear(self):
        rx = self._serial.readline()
        self._serial.reset_input_buffer()


if __name__ == '__main__':
    cd33 = CD33('COM13')
    cd33.send_command(cd33.MODE_AVG_MID)
    sleep(1)

    print('Serial Number:', cd33.serial_number)
    print('Measure AVG mode', cd33.send_command(CD33.MODE_AVG_READ, False))

    period = 1  # sec

    maxcnt = 1000
    cnt = 0
    stime = time.time()
    print(cd33.send_command(CD33.START_MEASURE, False, False))
    etime = stime+period
    while True:
        print(cd33.read_val_continue())
        t = time.time()
        cnt = cnt+1
        if(t > etime):
            etime = t
            break
    print('end')
    cd33.send_command(CD33.STOP_MEASURE)
