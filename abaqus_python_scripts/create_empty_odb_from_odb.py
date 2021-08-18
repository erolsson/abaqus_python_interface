from __future__ import print_function, division

import odbAccess
from abaqusConstants import DEFORMABLE_BODY, THREE_D
import os
import sys


def _copy_node_and_elements(to_odb_base, from_odb_base):
    nodal_data = from_odb_base.nodes
    if len(nodal_data) > 0:
        node_labels = []
        nodal_coordinates = []
        for n in nodal_data:
            node_labels.append(n.label)
            nodal_coordinates.append(n.coordinates)
        to_odb_base.addNodes(labels=node_labels, coordinates=nodal_coordinates)

    element_data = from_odb_base.elements
    element_dict = {}

    for e in element_data:
        element_type = e.type
        if element_type not in element_dict:
            element_dict[element_type] = {'labels': [], 'connectivity': []}
        element_dict[element_type]['labels'].append(e.label)
        element_dict[element_type]['connectivity'].append(e.connectivity)

    for element_type, element_data in element_dict.iteritems():
        to_odb_base.addElements(labels=element_data['labels'], connectivity=element_data['connectivity'],
                                type=element_type)


def _copy_sets(to_odb_base, from_odb_base):
    for node_set_name in from_odb_base.nodeSets.keys():
        node_set = from_odb_base.nodeSets[node_set_name]
        to_odb_base.NodeSet(name=node_set_name, nodes=node_set.nodes)

    for element_set_name in from_odb_base.elementSets.keys():
        element_set = from_odb_base.elementSets[element_set_name]
        to_odb_base.ElementSet(name=element_set_name, elements=element_set.elements)


def create_empty_odb(new_odb_file_name, old_odb_file_name):
    """
    :param new_odb_file_name:   Filename including path for the new odb
    :param old_odb_file_name:   Filename including path for the odb file containing the geometry
    :return:                    Nothing
    """

    new_odb = odbAccess.Odb(name=os.path.basename(new_odb_file_name), path=new_odb_file_name)
    old_odb = odbAccess.openOdb(old_odb_file_name, readOnly=True)
    # Copying the part and copying the nodes in that part
    for part_name in old_odb.parts.keys():
        old_part = old_odb.parts[part_name]
        new_part = new_odb.Part(name=part_name, embeddedSpace=THREE_D, type=old_part.type)
        _copy_node_and_elements(new_part, old_part)
        _copy_sets(new_part, old_part)
        new_odb.update()
        new_odb.save()

    # Copying the instances and copying the nodes
    for instance_name in old_odb.rootAssembly.instances.keys():
        old_instance = old_odb.rootAssembly.instances[instance_name]
        try:
            new_part = new_odb.parts[instance_name]
        except KeyError:
            try:
                new_part = new_odb.Part(name=instance_name, embeddedSpace=THREE_D,
                                        type=old_odb.parts[instance_name].type)
            except KeyError:
                new_part = new_odb.Part(name=instance_name, embeddedSpace=THREE_D, type=DEFORMABLE_BODY)

        # Copying the instance nodes to the part with the same name
        _copy_node_and_elements(new_part, old_instance)

        new_instance = new_odb.rootAssembly.Instance(name=instance_name, object=new_odb.parts[instance_name])
        _copy_sets(new_instance, old_instance)
        new_odb.update()
        new_odb.save()
    new_odb.close()
    old_odb.close()


if __name__ == '__main__':
    old_file = sys.argv[-1]
    new_file = sys.argv[-2]
    create_empty_odb(new_file, old_file)
