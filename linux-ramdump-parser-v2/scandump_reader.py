# Copyright (c) 2016-2017, The Linux Foundation. All rights reserved.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 and
# only version 2 as published by the Free Software Foundation.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.


import re
import os
from print_out import print_out_str


class Scandump_v2():

    def __init__(self, core, ramdump, version):
        self.core = core
        self.regs = {}
        self.version = version
        self.ramdump = ramdump
        self.init_missing_regs()

    def init_missing_regs(self):
        self.regs['currentEL'] = 0
        self.regs['spsr_el1'] = 0
        self.regs['spsr_el2'] = 0
        self.regs['spsr_el3'] = 0
        self.regs['cpu_state_0'] = 0
        self.regs['cpu_state_1'] = 0
        self.regs['cpu_state_3'] = 0
        self.regs['cpu_state_4'] = 0
        self.regs['cpu_state_5'] = 0

    def prepare_dict(self):
        input_file = "scandump"
        input_file_name = "{0}_core_{1}.cmm".format(input_file, (self.core))
        output = os.path.join(self.ramdump.outdir, input_file_name)
        if os.path.exists(output):
            fd = open(output, "r")
            for line in fd:
                matchObj = re.match('^REGISTER.SET ([xse].*[0-9]+)\s(0x[0-9a-f]{0,})', line, re.M | re.I)
                if matchObj:
                    regVal = matchObj.group(2)
                    if regVal == "0x":
                        regVal = "0x0000000000000000"
                    self.regs[(matchObj.group(1)).lower()] = int(regVal, 16)
                else:
                    matchObj = re.match('^REGISTER.SET (PC)\s(0x[0-9a-f]{0,})', line, re.M | re.I)
                    if matchObj:
                        regVal = matchObj.group(2)
                        if regVal == "0x":
                            regVal = "0x0000000000000000"
                        self.regs[matchObj.group(1).lower()] = int(regVal, 16)
                    else:
                        continue
            return self.regs
        else:
            return None

    def dump_core_pc(self, ram_dump):
        pc = self.regs['pc']
        if ram_dump.arm64:
            lr = self.regs['x30']
            bt = self.regs['sp_el1']
            fp = self.regs['x29']
        else:
            lr = self.regs['r14_svc']
            bt = self.regs['r13_svc']
            fp = self.regs['r11']

        a = ram_dump.unwind_lookup(pc)
        if a is not None:
            symname, offset = a
        else:
            symname = 'UNKNOWN'
            offset = 0
        print_out_str(
            'Core {3} PC: {0}+{1:x} <{2:x}>'.format(symname, offset,
                                                    pc, self.core))
        a = ram_dump.unwind_lookup(lr)
        if a is not None:
            symname, offset = a
        else:
            symname = 'UNKNOWN'
            offset = 0
        print_out_str(
            'Core {3} LR: {0}+{1:x} <{2:x}>'.format(symname, offset,
                                                    lr, self.core))
        print_out_str('')
        ram_dump.unwind.unwind_backtrace(bt, fp, pc, lr, '')
        print_out_str('')

