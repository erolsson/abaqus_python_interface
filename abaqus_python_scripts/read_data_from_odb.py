from __future__ import print_function, division

import pickle
import sys

from abaqus_constants import output_positions
from odb_io_functions import read_field_from_odb


parameter_pickle_name = sys.argv[-2]
results_pickle_name = sys.argv[-1]

with open(parameter_pickle_name, 'rb') as parameter_pickle:
    data = pickle.load(parameter_pickle)

field_id = str(data['field_id'])
odb_file_name = str(data['odb_file_name'])
step_name = str(data['step_name'])
frame_number = data['frame_number']
set_name = str(data['set_name'])
instance_name = str(data['instance_name'])
get_position_numbers = data['get_position_numbers']
get_frame_value = data['get_frame_value']
position = output_positions[str(data['position'])]
coordinate_system = data.get('coordinate_system', None)
if coordinate_system is not None and not isinstance(coordinate_system, dict):
    coordinate_system = str(coordinate_system)
rotating_system = data.get('deform_system', True)

field_data = read_field_from_odb(field_id, odb_file_name, step_name, frame_number, set_name,
                                 instance_name=instance_name, get_position_numbers=get_position_numbers,
                                 get_frame_value=get_frame_value, position=position,
                                 coordinate_system=coordinate_system, rotating_system=rotating_system)

data_dict = {}

if not get_position_numbers and not get_frame_value:
    data_dict['data'] = field_data
else:
    data_dict['data'] = field_data[0]
    if get_frame_value:
        data_dict['frame_value'] = field_data[1]
        pos_idx = 2
    else:
        pos_idx = 1
    data_dict['node_labels'] = field_data[pos_idx]
    data_dict['element_labels'] = field_data[pos_idx + 1]

with open(results_pickle_name, 'wb') as results_pickle:
    pickle.dump(data_dict, results_pickle)
