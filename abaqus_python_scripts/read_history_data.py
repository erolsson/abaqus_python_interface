import pickle
import sys

import numpy as np

from visualization import * # noqa
import xyPlot

from abaqusConstants import POINT_LIST, ELEMENT_NODAL, TRUE_DISTANCE, UNDEFORMED, PATH_POINTS, COMPONENT
from abaqus_constants import output_positions

from utilities import OpenOdb

# Getting rid of the flake8 issues that session is undefined
session = session # noqa


def main():
    pickle_file_name = sys.argv[-1]
    with open(pickle_file_name, 'r') as parameter_pickle:
        parameters = pickle.load(parameter_pickle)

    odb_file_name = str(parameters['odb_filename'])
    variable = str(parameters['variable'])
    output_position = output_positions[str(parameters['output_position'])]
    data_filename = str(parameters['data_filename'])
    component = None
    if 'component' in parameters:
        component = str(parameters['component'])

    with OpenOdb(odb_file_name, read_only=True) as odb:


xyDataListFromField(...)