# Copyright (c) 2016, The Linux Foundation. All rights reserved.

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
        input_file_name = "{0}_core{1}.cmm".format(input_file, (self.core - 4))
        output = os.path.join(self.ramdump.outdir, input_file_name)
        fd = open(output, "r")
        for line in fd:
            matchObj = re.match('^REGISTER.SET ([xse].*[0-9]+)\s(0x[0-9a-f]{0,})', line, re.M | re.I)
            if matchObj:
                regVal = matchObj.group(2)
                if regVal == "0x":
                    regVal = "0x0000000000000000"
                self.regs[(matchObj.group(1)).lower()] = int(regVal, 16)
            else:
                continue
        return self.regs
