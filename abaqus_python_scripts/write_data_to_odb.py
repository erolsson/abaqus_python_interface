from __future__ import print_function, division

import sys
import pickle

import numpy as np

from odbAccess import OdbError

from odb_io_functions import write_field_to_odb
from abaqus_constants import output_positions, invariants


def write_data_to_odb(array_file_name, pickle_file_name):
    field = np.load(array_file_name)
    with open(pickle_file_name, 'rb') as pickle_file:
        data = pickle.load(pickle_file)
    field_id = str(data['field_id'])
    instance_name = str(data['instance_name'])
    set_name = str(data['set_name'])
    odb_file = str(data['odb_file'])
    step_name = str(data['step_name'])
    step_description = str(data['step_description'])
    field_description = str(data['field_description'])
    frame_number = data['frame_number']
    frame_value = data['frame_value']
    requested_invariants = data.get('invariants', [])
    position = output_positions[str(data['position'])]

    requested_invariants = [invariants[str(inv)] for inv in requested_invariants]
    try:
        write_field_to_odb(field, field_id, odb_file, step_name=step_name, instance_name=instance_name,
                           set_name=set_name, step_description=step_description, frame_number=frame_number,
                           frame_value=frame_value, field_description=field_description, position=position,
                           invariants=requested_invariants)
    except OdbError as e:
        with open(pickle_file_name, 'wb') as pickle_file:
            pickle.dump({'ERROR': ["problems in writing data to the odb " + odb_file, str(e)]}, pickle_file)


if __name__ == '__main__':
    write_data_to_odb(sys.argv[-2], sys.argv[-1])
