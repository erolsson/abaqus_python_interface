from __future__ import print_function, division

from collections import OrderedDict
import pickle
import sys

from utilities import OpenOdb

odb_filename = sys.argv[-2]
results_pickle_file = sys.argv[-1]
with OpenOdb(odb_filename, read_only=True) as odb:
    odb_dict = {
        "steps": OrderedDict(),
        "rootAssembly": {
            "instances": {},
            "nodeSets": odb.rootAssembly.nodeSets.keys(),
            "elementSets": odb.rootAssembly.elementSets.keys()
        }
    }

    for instance_name in odb.rootAssembly.instances.keys():
        instance = odb.rootAssembly.instances[instance_name]
        odb_dict["rootAssembly"]["instances"][instance_name] = {
            "nodeSets": instance.nodeSets.keys(),
            "elementSets": instance.elementSets.keys(),
        }

    for step_name in odb.steps.keys():
        odb_dict["steps"][step_name] = OrderedDict()
        for frame_number in range(len(odb.steps[step_name].frames)):
            frame = {'fieldOutputs': odb.steps[step_name].frames[frame_number].fieldOutputs.keys()}
            odb_dict["steps"][step_name][frame_number] = frame

    with open(results_pickle_file, 'wb') as results_pickle:
        pickle.dump(odb_dict, results_pickle)
