#!/usr/bin/env python
# -*- coding:utf-8 -*-

import rospy,roslib
import serial
from time import sleep

DEV_PORT = "/dev/rfcomm1"
SYNC_BYTE = 0xaa


def main():
    print "Hello World"
    while True:
        dev.update()
        if dev.is_updated:
            dev.is_updated = False
            print "Med:",
            print dev.meditation,
            print "    Att:",
            print dev.attention,
            print "    signal:",
            print dev.poor_signal


class MindWaveMobile(object):
    def __init__(self, port='/dev/rfcomm1'):
        print "initializing"
        self.meditation = 0
        self.attention = 0
        self.poor_signal = 0
        self.raw_values = []
        self.asic_eeg_power_int = [0 for i in range(8)]
        self.is_updated = False
        self.dongle = serial.Serial(port, baudrate=115200, timeout=0.001)  # serialのポート
        self.in_buffer = []  # int型,受信値の配列
        self.reload_buffer()

    def reload_buffer(self):  # seialの受信バッファをすべて数値配列に変換
        self.in_buffer += [ord(b) for b in list(self.dongle.read(1000))]
        sleep(0.1)

    def parse_payload(self, payload):
        while len(payload) > 0:
            code = payload.pop(0)
            # print "type:",
            # print type(code),
            # print "      ",
            # print hex(code),
            if code >= 0x80:    # multi-bytes value
                vlength = payload.pop(0)
                if code == 0x80:
                    high_word = payload.pop(0)
                    low_word = payload.pop(0)
                    self.raw_values.append(high_word * 255 + low_word)
                    if (len(self.raw_values)) > 512:
                        self.raw_values.pop(0)
                elif code == 0x83:
                    # ASIC_EEG_POWER_INT
                    # delta, theta, low-alpha, high-alpha, low-beta, high-beta,
                    # low-gamma, high-gamma
                    self.asic_eeg_power_int = []
                    for i in range(8):
                        self.asic_eeg_power_int.append(
                            gen_uint24_t(payload.pop(0), payload.pop(0), payload.pop(0)))
                else:   # ERROR
                    pass
            else:               # single-byte value
                val = payload.pop(0)
                self.is_updated = True
                if code == 0x02:
                    self.poor_signal = val
                elif code == 0x04:
                    self.attention = val
                elif code == 0x05:
                    self.meditation = val
                else:
                    pass

    def update(self):
        while 1:
            if not self.wait_sync():
                continue
            self.in_buffer.pop(0)   # perge sync bytes
            self.in_buffer.pop(0)

            plen = SYNC_BYTE       # perge additional sync bytes
            while plen == SYNC_BYTE:    # in sync
                if len(self.in_buffer) == 0:
                    return False
                plen = self.in_buffer.pop(0)
                if plen == SYNC_BYTE:
                    continue
                else:                   # end sync
                    break
            if plen > SYNC_BYTE:  # plen must smaller than 0xaa(170 in dec)
                continue
            if (len(self.in_buffer) < plen+1):
                return False

            chksum = 0
            for byte in self.in_buffer[:plen]:
                chksum += byte
            chksum = chksum & ord('\xff')
            chksum = (~chksum) & ord('\xff')
            payload = self.in_buffer[:plen+1]
            self.in_buffer = self.in_buffer[plen+1:]
            if chksum != payload.pop():  # checksum error
                continue
            else:
                self.parse_payload(payload)
                return

    def wait_sync(self):
        while self.in_buffer[:2] != [SYNC_BYTE,SYNC_BYTE]:
            retry = 0
            while len(self.in_buffer) <= 3:
                retry += 1
                if retry > 3:
                    return False
                self.reload_buffer()
            self.in_buffer.pop(0)
        return True


def gen_uint24_t(b1, b2, b3):
    return 255 * 255 * b1 + 255 * b2 + b3


dev = MindWaveMobile(DEV_PORT)
if __name__ == '__main__':
    main()
