# Copyright (c) 2017, The Linux Foundation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#
#   * Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#
#   * Neither the name of The Linux Foundation nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import struct

"""dictionary mapping from (hw_id, client_id, version) to class CacheDump"""
lookuptable = {}


def lookup_tlb_type(hwid, client_id, version):
    """defaults to CacheDump() if no match found"""
    return lookuptable.get((hwid, client_id, version), TlbDump())


def formatwidth(string, limit):
    if len(string) >= limit:
        return string[0:limit]
    formatstr = '{{0:{0}}}'.format(limit)
    return formatstr.format(string)

class TableOutputFormat:
    """ Not sure if using PrettyTable (python lib) is a good idea, since people
    would need to install it"""

    def __init__(self):
        self.titlebar = []
        self.datafmt = []
        self.have_printed_title = False
        self.separator = ' '

    def addColumn(self, string, datafmt='{0}', width=0):
        width = max(len(string), width)
        string = formatwidth(string, width)
        self.titlebar.append(string)
        self.datafmt.append(datafmt)

    def printline(self, array, outfile):
        if (len(array) != len(self.titlebar)):
            raise Exception('BadTableDataSize', array, self.titlebar)

        if (not self.have_printed_title):
            self.have_printed_title = True
            outfile.write(self.separator.join(self.titlebar))
            outfile.write('\n')

        for item, title, fmt in zip(array, self.titlebar, self.datafmt):
            item = fmt.format(item)
            item = formatwidth(item, len(title))
            outfile.write(item)
            outfile.write(self.separator)

        outfile.write('\n')


class TlbDump(object):
    """ Class to describe a method to parse a particular type of tlbdump.
    Users should not make instances of this class."""
    def __init__(self):
        """do nothing"""

    def parse(self, start, end, ramdump, outfile):
        """Called from debug_image_v2.py. Overriden by child classes"""
        raise NotImplementedError

class TlbDumpType(TlbDump):
    def __init__(self):
        super(TlbDumpType, self).__init__()
        self.tableformat = TableOutputFormat()
        self.tableformat.addColumn('Way', '{0:01x}')
        self.tableformat.addColumn('Set', '{0:03x}')
        self.ramdump = None
        self.linefmt = None

    def add_table_data_columns(self):
        for i in range(0, self.LineSize):
            str = "DATA{0}".format(i)
            self.tableformat.addColumn(str, '{0:08x}', 8)

    def read_line(self, start):
        if self.linefmt is None:
            self.linefmt = '<'
            self.linefmt += 'I'* self.LineSize
        return self.ramdump.read_string(start, self.linefmt, virtual=False)


class TlbDumpType_v1(TlbDumpType):
    def __init__(self):
        super(TlbDumpType_v1, self).__init__()

    def parse(self, start, end, ramdump, outfile):
        self.ramdump = ramdump
        self.add_table_data_columns()

        for nset in range(self.NumSets):
            for nway in range(self.NumWays):
                if start > end:
                    raise Exception('past the end of array')

                output = [nway, nset]
                line = self.read_line(start)
                output.extend(line)
                self.tableformat.printline(output, outfile)
                start = start + self.LineSize * 0x4

class TlbDumpType_v2(TlbDumpType):
    def __init__(self):
        super(TlbDumpType_v2, self).__init__()
        self.tableformat.addColumn('RAM')
        self.tableformat.addColumn('TYPE')
        self.tableformat.addColumn('PA', '{0:016x}', 16)
        self.tableformat.addColumn('VA', '{0:016x}', 16)
        self.tableformat.addColumn('VALID')
        self.tableformat.addColumn('VMID', '{0:02x}', 4)
        self.tableformat.addColumn('ASID', '{0:04x}', 4)
        self.tableformat.addColumn('S1_MODE', '{0:01x}', 7)
        self.tableformat.addColumn('S1_LEVEL', '{0:01x}', 8)
        self.tableformat.addColumn('SIZE')

    def parse(self, start, end, ramdump, outfile):
        self.ramdump = ramdump
        self.add_table_data_columns()

        ram = 0
        for nway in range(self.NumWaysRam0):
            offset = 0
            for nset in range(self.NumSetsRam0):
                if start > end:
                    raise Exception('past the end of array')

                output = [nway, nset]
                line = self.read_line(start)
                self.parse_tag_fn(output, line, nset, nway, ram, offset)
                output.extend(line)
                self.tableformat.printline(output, outfile)
                start = start + self.LineSize * 0x4
                offset = offset + 0x1000

        ram = 1
        for nway in range(self.NumWaysRam0):
            offset = 0
            for nset in range(self.NumSetsRam1):
                if start > end:
                    raise Exception('past the end of array')

                output = [nway, nset]
                line = self.read_line(start)
                self.parse_tag_fn(output, line, nset, nway, ram, offset)
                output.extend(line)
                self.tableformat.printline(output, outfile)
                start = start + self.LineSize * 0x4
                offset = (offset + 0x1000)

class L1_TLB_KRYO2XX_GOLD(TlbDumpType_v2):
    def __init__(self):
        super(L1_TLB_KRYO2XX_GOLD, self).__init__()
        self.unsupported_header_offset = 0
        self.LineSize = 4
        self.NumSetsRam0 =  0x100
        self.NumSetsRam1 =  0x3c
        self.NumWaysRam0 = 4
        self.NumWaysRam1 = 2

    def parse_tag_fn(self, output, data, nset, nway, ram, offset):
        tlb_type = self.parse_tlb_type(data)

        s1_mode = (data[0] >> 2) & 0x3

        s1_level = data[0] & 0x3

        pa = (data[2] >> 4) * 0x1000
        pa = pa + offset

        va_l = (data[1] >> 2)
        va_h = (data[2]) & 0x7
        va = (va_h << 45) | (va_l << 16)
        va = va + offset

        if ((va >> 40) & 0xff )== 0xff:
            va = va + 0xffff000000000000

        valid = (data[2] >> 3) & 0x1

        vmid_1 = (data[0] >> 26) & 0x3f
        vmid_2 = data[1] & 0x3
        vmid = (vmid_2 << 6) | vmid_1

        asid = (data[0] >> 10) & 0xffff

        size = self.parse_size(data, ram, tlb_type)
        output.append(ram)
        output.append(tlb_type)
        output.append(pa)
        output.append(va)
        output.append(valid)
        output.append(vmid)
        output.append(asid)
        output.append(s1_mode)
        output.append(s1_level)
        output.append(size)

    def parse_tlb_type(self, data):
        type_num = (data[3] >> 20) & 0x1
        if type_num == 0x0:
            s1_level = data[0] & 0x3
            if s1_level == 0x3:
                return "IPA"
            else:
                return "REG"
        else:
            return "WALK"

    def parse_size(self, data, ram, tlb_type):
        size = (data[0] >> 6) & 0x7
        if tlb_type == "REG":
            if ram == 0:
                if size == 0x0:
                    return "4KB"
                elif size == 0x1:
                    return "16KB"
                else:
                    return "64KB"
            else:
                if size == 0x0:
                    return "1MB"
                elif size == 0x1:
                    return "2MB"
                elif size == 0x2:
                    return "16MB"
                elif size == 0x3:
                    return "32MB"
                elif size == 0x4:
                    return "512MB"
                else:
                    return "1GB"
        else:
                if size == 0x1:
                    return "4KB"
                elif size == 0x3:
                    return "16KB"
                elif size == 0x4:
                    return "64KB"

class L1_TLB_A53(TlbDumpType_v1):
    def __init__(self):
        super(L1_TLB_A53, self).__init__()
        self.unsupported_header_offset = 0
        self.LineSize = 4
        self.NumSets = 0x100
        self.NumWays = 4

class L1_TLB_KRYO3XX_GOLD(TlbDumpType_v2):
    def __init__(self):
        super(L1_TLB_KRYO3XX_GOLD, self).__init__()
        self.unsupported_header_offset = 0
        self.LineSize = 4
        self.NumSetsRam0 =  0x100
        self.NumSetsRam1 =  0x3c
        self.NumWaysRam0 = 4
        self.NumWaysRam1 = 2

    def parse_tag_fn(self, output, data, nset, nway, ram, offset):
        #tlb_type = self.parse_tlb_type(data)

        s1_mode = (data[0] >> 2) & 0x3

        s1_level = data[0] & 0x3

        pa_l = data[2] >> 14
        pa_h =  (data[3])& 0x1fff
        pa = (pa_h << 18 | pa_l) * 0x1000
        pa = pa + offset

        va_l = (data[1] >> 10)
        va_h = (data[2]) & 0x3ff
        va = ((va_h << 22) | (va_l)) * 0x1000
        va = va + offset

        if ((va >> 40) & 0xff )== 0xff:
            va = va + 0xffff000000000000

        valid = (data[2] >> 11) & 0x1

        vmid_1 = (data[0] >> 26) & 0x3f
        vmid_2 = data[1] & 0x3ff
        vmid = (vmid_2 << 6) | vmid_1

        asid = (data[0] >> 10) & 0xffff

        size = self.parse_size(data, ram, tlb_type)
        output.append(ram)
        output.append("N/A")
        output.append(pa)
        output.append(va)
        output.append(valid)
        output.append(vmid)
        output.append(asid)
        output.append(s1_mode)
        output.append(s1_level)
        output.append(size)

    def parse_tlb_type(self, data):
        type_num = (data[3] >> 20) & 0x1
        if type_num == 0x0:
            s1_level = data[0] & 0x3
            if s1_level == 0x3:
                return "IPA"
            else:
                return "REG"
        else:
            return "WALK"

    def parse_size(self, data, ram, tlb_type):
        size = (data[0] >> 6) & 0x7
        if ram == 0:
            if size == 0x0:
                return "4KB"
            elif size == 0x1:
                return "16KB"
            else:
                return "64KB"
        else:
            if size == 0x0:
                return "1MB"
            elif size == 0x1:
                return "2MB"
            elif size == 0x2:
                return "16MB"
            elif size == 0x3:
                return "32MB"
            elif size == 0x4:
                return "512MB"
            else:
                return "1GB"

class L1_TLB_KRYO3XX_SILVER(TlbDumpType_v1):
    def __init__(self):
        super(L1_TLB_KRYO3XX_SILVER, self).__init__()
        self.unsupported_header_offset = 0
        self.LineSize = 4
        self.NumSets = 0x100
        self.NumWays = 4

# "sdm845"
lookuptable[("sdm845", 0x20, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm845", 0x21, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm845", 0x22, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm845", 0x23, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm845", 0x24, 0x14)] = L1_TLB_KRYO3XX_GOLD()
lookuptable[("sdm845", 0x25, 0x14)] = L1_TLB_KRYO3XX_GOLD()
lookuptable[("sdm845", 0x26, 0x14)] = L1_TLB_KRYO3XX_GOLD()
lookuptable[("sdm845", 0x27, 0x14)] = L1_TLB_KRYO3XX_GOLD()

# "sdm670"
lookuptable[("sdm670", 0x20, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm670", 0x21, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm670", 0x22, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm670", 0x23, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm670", 0x24, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm670", 0x25, 0x14)] = L1_TLB_KRYO3XX_SILVER()
lookuptable[("sdm670", 0x26, 0x14)] = L1_TLB_KRYO3XX_GOLD()
lookuptable[("sdm670", 0x27, 0x14)] = L1_TLB_KRYO3XX_GOLD()

# "msm8998"
lookuptable[("8998", 0x20, 0x14)] = L1_TLB_A53()
lookuptable[("8998", 0x21, 0x14)] = L1_TLB_A53()
lookuptable[("8998", 0x22, 0x14)] = L1_TLB_A53()
lookuptable[("8998", 0x23, 0x14)] = L1_TLB_A53()
lookuptable[("8998", 0x24, 0x14)] = L1_TLB_KRYO2XX_GOLD()
lookuptable[("8998", 0x25, 0x14)] = L1_TLB_KRYO2XX_GOLD()
lookuptable[("8998", 0x26, 0x14)] = L1_TLB_KRYO2XX_GOLD()
lookuptable[("8998", 0x27, 0x14)] = L1_TLB_KRYO2XX_GOLD()


lookuptable[("8998", 0x40, 0x14)] = L1_TLB_A53()
lookuptable[("8998", 0x41, 0x14)] = L1_TLB_A53()
lookuptable[("8998", 0x42, 0x14)] = L1_TLB_A53()
lookuptable[("8998", 0x43, 0x14)] = L1_TLB_A53()
lookuptable[("8998", 0x44, 0x14)] = L1_TLB_KRYO2XX_GOLD()
lookuptable[("8998", 0x45, 0x14)] = L1_TLB_KRYO2XX_GOLD()
lookuptable[("8998", 0x46, 0x14)] = L1_TLB_KRYO2XX_GOLD()
lookuptable[("8998", 0x47, 0x14)] = L1_TLB_KRYO2XX_GOLD()

