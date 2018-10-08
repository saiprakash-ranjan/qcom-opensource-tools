# Copyright (c) 2018, The Linux Foundation. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 and
# only version 2 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

from parser_util import cleanupString
from parser_util import register_parser, RamParser
from print_out import print_out_str

@register_parser('--pstore', 'Extract event logs from pstore')
class PStore(RamParser):

    def calculate_percpu_eventbuf_size(self, base_addr):
        event_zone_addr = self.ramdump.read_u64(base_addr +
                          (self.ramdump.field_offset('struct ramoops_context', 'eprzs')))
        event_zone_addr = self.ramdump.read_u64(event_zone_addr)
        start_addr = self.ramdump.read_u32(event_zone_addr +
                     (self.ramdump.field_offset('struct persistent_ram_zone', 'paddr')))
        percpu_size = self.ramdump.read_u32(event_zone_addr +
                      (self.ramdump.field_offset('struct persistent_ram_zone', 'size')))
        return start_addr, percpu_size

    def print_pstore(self, pstore_out, addr, size):
        pstore = self.ramdump.read_physical(addr, size)
        pstore_out.write(cleanupString(pstore.decode('ascii', 'ignore')) + '\n')

    def calculate_console_size(self, base_addr):
        console_zone_addr = self.ramdump.read_u64(base_addr +
                            (self.ramdump.field_offset('struct ramoops_context', 'cprz')))
        start_addr = self.ramdump.read_u32(console_zone_addr +
                     (self.ramdump.field_offset('struct persistent_ram_zone', 'paddr')))
        console_size = self.ramdump.read_u32(console_zone_addr +
                       (self.ramdump.field_offset('struct persistent_ram_zone', 'size')))
        return start_addr, console_size

    def extract_console_logs(self, base_addr):
        '''
        Parses the console logs from pstore
        '''
        start_addr, console_size = self.calculate_console_size(base_addr)
        pstore_out = self.ramdump.open_file('console_logs.txt')
        self.print_pstore(pstore_out, start_addr, console_size)
        pstore_out.close()

    def extract_io_event_logs(self, base_addr):
        '''
        Parses the RTB data (register read/writes) stored in the persistent
        ram zone. Data is extracted on per cpu basis into separate per core
        files.
        '''
        start_addr, percpu_size = self.calculate_percpu_eventbuf_size(base_addr)
        nr_cpus = self.ramdump.get_num_cpus()
        for cpu in range(0,nr_cpus):
            pstore_out = self.ramdump.open_file('rtb_core_{}.txt'.format(cpu))
            cpu_offset = percpu_size*cpu
            self.print_pstore(pstore_out, start_addr+cpu_offset, percpu_size)
            pstore_out.close()

    def parse(self):
        base_addr = self.ramdump.address_of('oops_cxt')
        self.extract_io_event_logs(base_addr)
        self.extract_console_logs(base_addr)

