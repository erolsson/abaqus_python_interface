from __future__ import print_function, division
from collections import defaultdict
import pickle
import sys

import numpy as np
from utilities import OpenOdb

parameter_pickle_file = sys.argv[-2]
results_pickle_file = sys.argv[-1]
with open(parameter_pickle_file, 'r') as parameter_pickle:
    parameters = pickle.load(parameter_pickle)
odb_filename = str(parameters['odb_filename'])
element_set = parameters.get("element_set", None)
if element_set:
    element_set = str(element_set)
instance_name = parameters.get("instance_name", None)
if instance_name:
    instance_name = str(instance_name)
all_element_data = defaultdict(dict)
with OpenOdb(odb_filename, read_only=True) as odb:
    if element_set is None:
        element_base = odb.rootAssembly.instances[instance_name].elements
    else:
        element_base = odb.rootAssembly.instances[instance_name].elementSets[element_set].elements
    nodes = {}
    node_list = odb.rootAssembly.instances[instance_name].nodes
    for i in range(len(node_list)):
        nodes[node_list[i].label] = node_list[i].coordinates

    for i in range(len(element_base)):
        e = element_base[i]
        element_data = all_element_data[e.type]
        element_nodal_coordinates = []
        for node_label in e.connectivity:
            element_nodal_coordinates.append(nodes[node_label])
        element_nodal_coordinates = np.array(element_nodal_coordinates)
        element_data[e.label] = element_nodal_coordinates

    with open(results_pickle_file, 'wb') as results_pickle:
        pickle.dump(all_element_data, results_pickle)
