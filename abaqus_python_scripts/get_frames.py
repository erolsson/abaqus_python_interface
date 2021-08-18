from __future__ import print_function, division

import pickle
import sys

from utilities import OpenOdb

odb_filename = sys.argv[-3]
step_name = sys.argv[-2]
results_pickle_file = sys.argv[-1]
with OpenOdb(odb_filename, read_only=True) as odb:
    with open(results_pickle_file, 'wb') as results_pickle:
        pickle.dump(range(len(odb.steps[step_name].frames)), results_pickle)
