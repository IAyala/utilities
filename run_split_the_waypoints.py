#!/usr/bin/env python
""" This script split a waypoints file into several files """
import codecs
import sys
import unicodedata
from argparse import ArgumentParser
from os import getcwd, mkdir
from os.path import exists, join, isdir
from re import sub
from shutil import rmtree

def convert_to_list(line):
    """ Convert Data to List """
    the_data_as_list = sub(r' +', ' ', line).split(' ')
    return the_data_as_list

def decode_line(line):
    """ Decode Line """
    return unicodedata.normalize('NFKD', line).encode('ascii', 'ignore').replace('\r\n', '\n')

def append_font_information():
    """ The information about the font """
    return ['t "Arial",-13,0,0,0, 700\r\n']

def non_empty_lines(lines):
    """ Select non empty lines """
    return [x for x in lines if len(x.replace(' ', '')) > 0]

class ItemType:
    """ The class to store Item features """
    def __init__(self, common_lines, file_identifier, validation_function, append_font_info):
        self.common_lines = common_lines
        self.file_identifier = file_identifier
        self.val_function = validation_function
        self.append_font_info = append_font_info
        self.items = []

    def validate_and_insert(self, raw_line_prev, raw_line_post):
        """ Insert if valid """
        if self.val_function(convert_to_list(raw_line_prev)):
            to_append = [raw_line_prev, raw_line_post]
            if self.append_font_info:
                to_append += append_font_information()
            self.items += to_append
            return True
        return False

    def get_items_to_write(self):
        """ Items to be written """
        return self.common_lines + self.items

    def get_file_pattern(self, root_path):
        """ The file patterns """
        return join(root_path, self.file_identifier)

class FileWriter:
    """ This class will write into files """
    def __init__(self, the_item_type, the_number_lines_per_item, max_items_per_file, root_path):
        self.common_lines = the_item_type.common_lines
        self.items = the_item_type.items
        if self.total_number_lines() % the_number_lines_per_item != 0:
            sys.exit(f'Items length: {len(self.items)} not multiple of {the_number_lines_per_item}')
        self.file_pattern = the_item_type.get_file_pattern(root_path)
        self.number_lines_per_item = the_number_lines_per_item
        self.max_items_per_file = max_items_per_file

    def get_decoded_lines(self, chunk_lines):
        """ Decode the lines """
        the_list = self.common_lines + chunk_lines
        decoded_lines = [decode_line(x) for x in the_list]
        return decoded_lines

    def get_items_to_write(self):
        """ Items that will be written """
        return self.common_lines + self.items

    def max_number_lines_for_file(self):
        """ Maximum number of lines per file """
        return self.max_items_per_file * self.number_lines_per_item

    def total_number_lines(self):
        """ Total number of lines """
        return len(self.items)

    def total_number_items(self):
        """ Number of items """
        return len(self.items) / self.number_lines_per_item  # Are divisible, checked in constructor

    def get_indexes_from_chunk(self, chunk_number):
        """ The indexes for the chunk """
        lower_index = self.max_number_lines_for_file() * chunk_number
        upper_index = min(
            self.total_number_lines(),
            self.max_number_lines_for_file() * (chunk_number + 1)
        )
        return lower_index, upper_index

    def write_chunk(self, chunk_id, file_path):
        """ Write this chunk """
        lower_index, upper_index = self.get_indexes_from_chunk(chunk_id)
        with open(file_path, 'w+', encoding='utf-8') as the_file:
            the_file.writelines(self.get_decoded_lines(self.items[lower_index:upper_index]))

    def number_chunks(self):
        """ How many chunks? """
        aux = divmod(self.total_number_items(), self.max_items_per_file)
        return aux[0] + 1  # First item of divmod function gives the div of parameters division

    def write_items(self):
        """ Write the items """
        for i in range(self.number_chunks()):
            file_path = f'{self.file_pattern}_{i}.wpt'
            self.write_chunk(i, file_path)
        return self.total_number_items(), self.number_chunks()

def get_common_lines(the_data):
    """ The common lines for all files """
    result = []
    for line in the_data:
        if not line.lower().startswith('w'):
            result.append(line)
        else:
            break
    return result

def get_items_from_data(the_data, the_item_types):
    """ Items from data """
    non_empty_data = non_empty_lines(the_data)
    for line_idx in range(len(non_empty_data) - 1):
        for one_item_type in the_item_types:
            the_prev = non_empty_data[line_idx]
            the_next = non_empty_data[line_idx + 1]
            if one_item_type.validate_and_insert(the_prev, the_next):
                break

def setup_output(root_path):
    """ If exists, remove and create new """
    the_output_path = join(root_path, 'output')
    if exists(the_output_path) and isdir(the_output_path):
        rmtree(the_output_path)
    mkdir(the_output_path)
    return the_output_path

def read_inputs():
    """ Inputs for the script """
    parser = ArgumentParser()
    parser.add_argument('waypointFile', help='Waypoint File (*.wpt file)')
    help_message = 'Maximum Number of Waypoints per File'
    parser.add_argument('max_waypoints_per_file', type=int, help=help_message)
    args = parser.parse_args()
    the_wpt_file = args.waypointFile
    if not exists(the_wpt_file):
        sys.exit(f'The file {the_wpt_file} does not exist')
    max_wpt_per_file = args.max_waypoints_per_file
    add_font_data = True  # This is hardcoded at the moment
    lines_per_item = 3  # As the previous variable is True, this must be 3
    return the_wpt_file, max_wpt_per_file, add_font_data, lines_per_item

def is_a_pz(list_items):
    """ Check if this is a PZ """
    return list_items[0] == 'W' and 'pz' in list_items[1].lower()

def is_a_waypoint(list_items):
    """ Check if this is a waypoint """
    return list_items[0] == 'W' and not is_a_pz(list_items)

if __name__ == "__main__":
    wpt_file, max_waypoints_per_file, must_add_font_data, number_lines_per_item = read_inputs()
    output_path = setup_output(getcwd())
    with codecs.open(wpt_file, encoding='utf-8') as the_wpts:
        data = the_wpts.readlines()
        the_common_lines = get_common_lines(data)
        item_types = [
            ItemType(the_common_lines, 'PZ', is_a_pz, must_add_font_data),
            ItemType(the_common_lines, 'SplittedWPT', is_a_waypoint, must_add_font_data),
        ]
        get_items_from_data(data, item_types)
        for item_type in item_types:
            the_writer = FileWriter(
                item_type,
                number_lines_per_item,
                max_waypoints_per_file,
                output_path
            )
            items_written, number_files = the_writer.write_items()
            message = f'{items_written} waypoints written in {number_files} '
            message += f'files of type: {item_type.file_identifier}'
            print(message)
