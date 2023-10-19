import pickle
import sys

import numpy as np

from visualization import * # noqa
import xyPlot

from abaqusConstants import POINT_LIST, ELEMENT_NODAL, TRUE_DISTANCE, UNDEFORMED, PATH_POINTS, COMPONENT, INVARIANT
from abaqus_constants import output_positions, invariants

from utilities import OpenOdb

# Getting rid of the flake8 issues that session is undefined
session = session # noqa


def main():
    pickle_file_name = sys.argv[-1]
    with open(pickle_file_name, 'r') as parameter_pickle:
        parameters = pickle.load(parameter_pickle)

    odb_file_name = str(parameters['odb_file_name'])
    field_id = str(parameters['field_id'])
    output_position = output_positions[str(parameters['position'])]
    data_filename = str(parameters['data_filename'])
    instace_name = str(parameters['instance_name'])
    args = {"outputPosition": output_position}
    if 'component' in parameters:
        component = str(parameters['component'])
        args["variable"] = (field_id, output_position, ((COMPONENT, component),))
    elif 'invariant' in parameters:
        invariant = str(invariants['invariant'])
        args["variable"] = (field_id, output_position, ((INVARIANT, invariant),))
    else:
        args["variable"] = (field_id, output_position)
    if "node_labels" in parameters:
        args["nodeLabels"] = (instace_name, parameters["node_labels"])

    if "element_labels" in parameters:
        args["elementLabels"] = (instace_name, parameters["element_labels"])

    if "element_sets" in parameters:
        args["elementSets"] = [str(eset) for eset in parameters["element_sets"]]
    if "node_sets" in parameters:
        args["nodeSets"] = [str(nset) for nset in parameters["node_sets"]]



    with OpenOdb(odb_file_name, read_only=True) as odb:
        args["odb"] = odb


        xyList = xyPlot.xyDataListFromField(**args)
        print(xyList)


if __name__ == '__main__':
    main()
