from abaqusConstants import NODAL, ELEMENT_NODAL, INTEGRATION_POINT, CYLINDRICAL
from abaqusConstants import MISES, PRESS


abaqus_constants = {'CYLINDRICAL': CYLINDRICAL}

output_positions = {
    'NODAL': NODAL,
    'ELEMENT_NODAL': ELEMENT_NODAL,
    'INTEGRATION_POINT': INTEGRATION_POINT}

invariants = {
    'MISES': MISES,
    'PRESS': PRESS
}

abaqus_constants.update(output_positions)
abaqus_constants.update(invariants)
