import pickle
import sys

import numpy as np

from visualization import * # noqa
import xyPlot

from abaqusConstants import POINT_LIST, ELEMENT_NODAL, TRUE_DISTANCE, UNDEFORMED, PATH_POINTS, COMPONENT, INVARIANT
from abaqusConstants import INTEGRATION_POINT
from abaqus_constants import output_positions, invariants

from utilities import OpenOdb

# Getting rid of the flake8 issues that session is undefined
session = session # noqa


def main():
    pickle_file_name = sys.argv[-2]
    data_file_name = sys.argv[-1]
    with open(pickle_file_name, 'r') as parameter_pickle:
        parameters = pickle.load(parameter_pickle)

    odb_file_name = str(parameters['odb_file_name'])
    field_id = str(parameters['field_id'])
    output_position = output_positions[str(parameters['output_position'])]
    variable_position = output_positions[str(parameters['variable_position'])]
    instance_name = str(parameters['instance_name'])
    args = {"outputPosition": output_position}
    if 'component' in parameters:
        component = str(parameters['component'])
        args["variable"] = ((field_id, variable_position, ((COMPONENT, component),)),)
    elif 'invariant' in parameters:
        invariant = str(invariants['invariant'])
        args["variable"] = ((field_id, variable_position, ((INVARIANT, invariant),)),)
    else:
        args["variable"] = ((field_id, variable_position),)

    if "node_labels" in parameters or "element_labels" in parameters:
        if "node_labels" in parameters:
            labels = parameters["node_labels"]
            arg = "nodeLabels"
        else:
            labels = parameters["element_labels"]
            arg = "elementLabels"
        if not isinstance(labels, str) and not hasattr(labels, '__iter__'):
            labels = [labels]
        args[arg] = ((instance_name, tuple([str(e) for e in labels])),)

    if "element_sets" in parameters:
        args["elementSets"] = [str(eset) for eset in parameters["element_sets"]]
    if "node_sets" in parameters:
        args["nodeSets"] = [str(nset) for nset in parameters["node_sets"]]

    with OpenOdb(odb_file_name, read_only=True) as odb:
        session.Viewport(name='Viewport: 1', origin=(0.0, 0.0), width=309.913116455078,
                         height=230.809509277344)
        session.viewports['Viewport: 1'].makeCurrent()
        session.viewports['Viewport: 1'].maximize()
        o7 = session.odbs[session.odbs.keys()[0]]
        session.viewports['Viewport: 1'].setValues(displayedObject=o7)
        args["odb"] = odb
        xyList = xyPlot.xyDataListFromField(**args)

        data_to_return = [np.array(data_list) for data_list in xyList]

    with open(data_file_name, 'wb') as data_pickle:
        pickle.dump(data_to_return, data_pickle)

if __name__ == '__main__':
    main()
