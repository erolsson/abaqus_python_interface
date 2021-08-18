from __future__ import print_function

import os
import pickle
import sys

from abaqusConstants import DEFORMABLE_BODY, THREE_D
import odbAccess

from odb_io_functions import add_element_set, add_node_set
from utilities import OpenOdb


def main():
    pickle_filename = sys.argv[-1]
    with open(pickle_filename, 'rb') as pickle_file:
        data_for_creating_odb = pickle.load(pickle_file)
    odb_file_name = str(data_for_creating_odb['odb_file_name'])
    instances = data_for_creating_odb['instance_data']
    odb = odbAccess.Odb(name=os.path.basename(odb_file_name), path=odb_file_name)
    odb.close()
    for instance in instances:
        with OpenOdb(odb_file_name, read_only=False) as odb:
            instance_name = str(instance['instance_name'])
            part = odb.Part(name=instance_name, embeddedSpace=THREE_D,
                            type=DEFORMABLE_BODY)  # Todo Implement 2D models
            part.addNodes(nodeData=instance['nodes'])
            for element_type, element_data in instance['elements'].iteritems():
                part.addElements(elementData=element_data, type=str(element_type))
            odb.rootAssembly.Instance(name=instance_name, object=part)

        for node_set_name, nodes in instance['node_sets'].iteritems():
            add_node_set(odb_file_name, str(node_set_name), nodes, instance_name)

        for element_set_name, elements in instance['element_sets'].iteritems():
            add_element_set(odb_file_name, str(element_set_name), elements, instance_name)


if __name__ == '__main__':
    main()
