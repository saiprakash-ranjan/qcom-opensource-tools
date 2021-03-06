# Copyright (c) 2012-2013, The Linux Foundation. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 and
# only version 2 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

from print_out import print_out_str
from parser_util import register_parser, RamParser


@register_parser('--print-pagetypeinfo', 'Print the pagetypeinfo')
class Pagetypeinfo(RamParser):

    def print_pagetype_info_per_zone(self, ramdump, zone, migrate_types):

        free_area_offset = ramdump.field_offset('struct zone', 'free_area')
        free_area_size = ramdump.sizeof('struct free_area')
        free_list_offset = ramdump.field_offset(
            'struct free_area', 'free_list')
        migratetype_names = ramdump.addr_lookup('migratetype_names')
        zone_name_offset = ramdump.field_offset('struct zone', 'name')
        zname_addr = ramdump.read_word(zone + zone_name_offset)
        zname = ramdump.read_cstring(zname_addr, 12)
        is_corrupt = False
        total_bytes = 0

        for mtype in range(0, migrate_types):
            mname_addr = ramdump.read_word(migratetype_names + mtype * 4)
            mname = ramdump.read_cstring(mname_addr, 12)
            pageinfo = ('zone {0:8} type {1:12} '.format(zname, mname))
            nums = ''
            total_type_bytes = 0
            for order in range(0, 11):

                area = zone + free_area_offset + order * free_area_size

                orig_free_list = area + free_list_offset + 8 * mtype
                curr = orig_free_list
                pg_count = -1
                first = True
                while True:
                    pg_count = pg_count + 1
                    next_p = ramdump.read_word(curr)
                    if next_p == curr:
                        if not first:
                            is_corrupt = True
                        break
                    first = False
                    curr = next_p
                    if curr == orig_free_list:
                        break
                nums = nums + ('{0:6}'.format(pg_count))
                total_type_bytes = total_type_bytes + \
                    pg_count * 4096 * (2 ** order)
            print_out_str(pageinfo + nums +
                          ' = {0} MB'.format(total_type_bytes / (1024 * 1024)))
            total_bytes = total_bytes + total_type_bytes

        print_out_str('Approximate total for zone {0}: {1} MB\n'.format(
            zname, total_bytes / (1024 * 1024)))
        if is_corrupt:
            print_out_str(
                '!!! Numbers may not be accurate due to list corruption!')

    def parse(self):
        migrate_types = self.ramdump.gdbmi.get_value_of('MIGRATE_TYPES')
        max_nr_zones = self.ramdump.gdbmi.get_value_of('__MAX_NR_ZONES')

        contig_page_data = self.ramdump.addr_lookup('contig_page_data')
        node_zones_offset = self.ramdump.field_offset(
            'struct pglist_data', 'node_zones')
        present_pages_offset = self.ramdump.field_offset(
            'struct zone', 'present_pages')
        sizeofzone = self.ramdump.sizeof('struct zone')
        zone = contig_page_data + node_zones_offset

        while zone < (contig_page_data + node_zones_offset + max_nr_zones * sizeofzone):
            present_pages = self.ramdump.read_word(zone + present_pages_offset)
            if not not present_pages:
                self.print_pagetype_info_per_zone(
                    self.ramdump, zone, migrate_types)

            zone = zone + sizeofzone
