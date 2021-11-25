from __future__ import print_function, division

from collections import namedtuple

import numpy as np

from abaqusConstants import INTEGRATION_POINT, ELEMENT_NODAL, NODAL, CYLINDRICAL, CENTROID, ELEMENT_FACE, TIME
from abaqusConstants import SCALAR, TENSOR_3D_FULL, VECTOR

from abaqus_constants import abaqus_constants
from utilities import OpenOdb

CoordinateSystem = namedtuple('CoordinateSystem', ['name', 'origin', 'point1', 'point2', 'system_type'])
cylindrical_system_z = CoordinateSystem(name='cylindrical', origin=(0., 0., 0.), point1=(1., 0., 0.),
                                        point2=(0., 1., 0.), system_type=CYLINDRICAL)


def read_field_from_odb(field_id, odb_file_name, step_name=None, frame_number=-1, set_name='', instance_name=None,
                        coordinate_system=None, rotating_system=False, position=INTEGRATION_POINT,
                        get_position_numbers=False, get_frame_value=False):
    """
    Function for reading a field from an odb-file
    :param field_id:                The ID of the field. example 'S'  for stresses
    :param odb_file_name:           Filename of the odb-file with the .odb extension
    :param step_name:               Name of the step to read from, default is None which takes the last step in
                                    odb_file_name
    :param frame_number:            Number of the frame to read from, beginning of step is 1 end of step is -1
    :param set_name:                Name of the set to read data from. Default is None which gives data for
                                    the whole instance
    :param instance_name:           Name of the instance to read from. Must be provided if the model consist of several
                                    instances. Default is None which only works if the model jut contains one instance
    :param coordinate_system:       A coordinate system object which has the members, name, origin, point1, point2
                                    and system_type. Default is None which gives the model system
    :param rotating_system:         A flag to specify if the system rotates which is useful for gears. Default is False
    :param position:                AbaqusConstant specifying the output position of the field like INTEGRATION_POINT
                                    or NODAL. Default is INTEGEATION_POINT
    :param get_position_numbers:    A flag if nodal and element numbers should be returned together with the data.
                                    Default is False
    :param get_frame_value:         Flag if the frame value should be provided with the data. Default is False

    :return:                        The function returns a numpy matrix with the field data.
                                    Depending on the flags it could also return double with the frame value as well
                                    as list with node and element numbers. The ordering of this objects is shown below

                                    if not get_position_numbers and not get_frame_value:
                                        return data
                                    elif not get_position_numbers:
                                        return data, frame_value
                                    elif not get_frame_value:
                                        return data, node_labels, element_labels
                                    else:
                                        return data, frame_value, node_labels, element_labels
    """
    read_only = True
    if coordinate_system is not None:
        coordinate_system = CoordinateSystem(str(coordinate_system['name']), coordinate_system['origin'],
                                             coordinate_system['point1'], coordinate_system['point2'],
                                             abaqus_constants[coordinate_system['system_type']])
        read_only = False
    with OpenOdb(odb_file_name, read_only=read_only) as odb:
        if not instance_name:
            if len(odb.rootAssembly.instances) == 1:
                base = odb.rootAssembly.instances[odb.rootAssembly.instances.keys()[0]]
            else:
                raise ValueError('odb has multiple instances, please specify an instance')
        else:
            base = odb.rootAssembly.instances[instance_name]
        if position in [INTEGRATION_POINT, CENTROID, ELEMENT_NODAL, ELEMENT_FACE]:
            set_dict = base.elementSets
            set_func = base.ElementSet
            all_name = 'ALL_ELEMENTS'
            object_list = base.elements
        else:
            set_dict = base.nodeSets
            set_func = base.NodeSet
            all_name = 'ALL_NODES'
            object_list = base.nodes

        if set_name == '':
            if all_name not in set_dict:
                objects = object_list
                set_func(name=all_name, elements=objects)
            element_set = set_dict[all_name]
        else:
            element_set = set_dict[set_name]

        field = odb.steps[step_name].frames[frame_number].fieldOutputs[field_id].getSubset(position=position)
        field = field.getSubset(region=element_set)
        frame_value = odb.steps[step_name].frames[frame_number].frameValue
        if coordinate_system is not None:
            if coordinate_system.name not in odb.rootAssembly.datumCsyses:
                transform_system = odb.rootAssembly.DatumCsysByThreePoints(name=coordinate_system.name,
                                                                           coordSysType=coordinate_system.system_type,
                                                                           origin=coordinate_system.origin,
                                                                           point1=coordinate_system.point1,
                                                                           point2=coordinate_system.point2)
            else:
                transform_system = odb.rootAssembly.datumCsyses[coordinate_system.name]

            if rotating_system:
                deformation_field = odb.steps[step_name].frames[frame_number].fieldOutputs['U']
                field = field.getTransformedField(transform_system, deformationField=deformation_field)
            else:
                field = field.getTransformedField(transform_system)
        field = field.values

        # ToDo: raise exception if field is empty
        n1 = len(field)
        n2 = 1 if type(field[0].data) is float else len(field[0].data)
        if n2 > 1:
            data = np.zeros((n1, n2))
        else:
            data = np.zeros(n1)
        node_labels = []
        element_labels = []
        for i, data_point in enumerate(field):
            data[i] = data_point.data
            if position in [NODAL, ELEMENT_NODAL]:
                node_labels.append(data_point.nodeLabel)
            elif position in [INTEGRATION_POINT, CENTROID, ELEMENT_NODAL, ELEMENT_FACE]:
                element_labels.append(data_point.elementLabel)

    if not get_position_numbers and not get_frame_value:
        return data
    elif not get_position_numbers:
        return data, frame_value
    elif not get_frame_value:
        return data, node_labels, element_labels
    else:
        return data, frame_value, node_labels, element_labels


def write_field_to_odb(field_data, field_id, odb_file_name, step_name, instance_name=None, set_name=None,
                       step_description='', frame_number=None, frame_value=None, field_description='', invariants=None,
                       position=INTEGRATION_POINT):
    """
    Function for writing a field to an odb to visualize the data

    :param field_data:              A numpy with the field data. It mut be ordered correctly and hence the function
                                    read_field_from_odb is recommended to get the correct ordering of the data
    :param field_id:                The ID of the field. example 'S'  for stresses
    :param odb_file_name:           Filename of the odb to write to
    :param step_name:               Name of the step to write to. Created if it does not exist.
    :param instance_name:           Name of the instance to write to. Must be provided if the model consist of several
                                    instances. Default is None which only works if the model jut contains one instance
    :param set_name:                Name of the set to read data from. Default is None which gives data for
                                    the whole instance
    :param step_description:        Description string of the step if it is created. Default is an empty string
    :param frame_number:            The number of the frame to write to. Default is None which creates a new frame
                                    last in the specified step
    :param frame_value:             Value of the frame if it is created. Default is None which gives the previous
                                    frame_value + 1.0 if there are any frames in the step, if not frame_value 0.
                                    is used as default
    :param field_description:       Description string of the field. Default is an empty string
    :param invariants:              A list of invariants for the field to be included in the odb. Specified as
                                    abaqusConstants. For example, if stresses are imported
                                        invariants=[MISES, MAX_PRINCIPAL]
                                    imports the von Mises stress and the maximum principal stress
    :param position:                The field output position where the data is written like INTEGRATION_POINT or
                                    UNIQUE_NODAL. Default is INTEGRATION_POINT

    :return:                        Nothing
    """
    with OpenOdb(odb_file_name, read_only=False) as odb:
        if step_name not in odb.steps:
            step = odb.Step(name=step_name, description=step_description, domain=TIME, timePeriod=1.)
        else:
            step = odb.steps[step_name]
        if instance_name == '':
            if len(odb.rootAssembly.instances) == 1:
                instance = odb.rootAssembly.instances[odb.rootAssembly.instances.keys()[0]]
            else:
                raise ValueError("The odb file consist of several instances, please specify an instance")
        else:
            instance = odb.rootAssembly.instances[instance_name]

        if position in [INTEGRATION_POINT, CENTROID, ELEMENT_NODAL, ELEMENT_FACE]:
            if set_name:
                objects = instance.elementSets[set_name].elements
            else:
                objects = instance.elements
        elif position == NODAL:
            if set_name:
                objects = instance.nodeSets[set_name].nodes
            else:
                objects = instance.nodes
        else:
            raise TypeError("The specified position is not a valid output position for abaqus")
        object_numbers = []
        for obj in objects:
            object_numbers.append(obj.label)
        field_types = {1: SCALAR, 6: TENSOR_3D_FULL, 3: VECTOR}

        if len(field_data.shape) == 1:
            field_data = field_data[:, np.newaxis]
        field_type = field_types[field_data.shape[1]]
        field_data_to_frame = tuple(field_data[:, :])
        if frame_value is None:
            if len(step.frames) > 0:
                frame_value = step.frames[len(step.frames)-1].frameValue + 1.0
            else:
                frame_value = 0.

        if frame_number is None or len(step.frames) == 0 or len(step.frames) <= frame_number:
            frame = step.Frame(incrementNumber=len(step.frames)+1, frameValue=frame_value, description='')
        else:
            frame = step.frames[frame_number]

        if invariants is None:
            invariants = []
        if field_id in frame.fieldOutputs:
            field = frame.fieldOutputs[field_id]
        else:
            field = frame.FieldOutput(name=field_id, description=field_description, type=field_type,
                                      validInvariants=invariants)
        field.addData(position=position, instance=instance, labels=object_numbers, data=field_data_to_frame)


def get_nodal_coordinates_from_node_set(odb_file_name, node_set_name, instance_name=None):
    """
    Function for getting the nodal coordinates of the nodes in a node set

    :param odb_file_name:   Name of the odb file where the set and nodes are located
    :param node_set_name:   Name of the node set
    :param instance_name:   Name of the instance if the set is an instance-based node set. Default is None which
                            assumes that the node set is located under odb.rootAssembly.nodeSets

    :return:                A dict with the node labels as the keys and numpy arrays with the coordinates of the node
    """
    # todo Implement exception if invalid set or instances are provided
    with OpenOdb(odb_file_name, read_only=True) as odb:
        if instance_name:
            node_set = odb.rootAssembly.instances[instance_name]
        else:
            node_set = odb.rootAssembly.nodeSets[node_set_name]
        node_dict = {}
        for node in node_set.nodes:
            node_dict[node.label] = node.coordinates
        odb.close()
        return node_dict


def flip_node_order(data, axis):      # ToDo implement flip around x and y axis as well
    """
    Function hat can be for flipping the data if symmetries are used when writing the field to an odb. Typical usage is
    when data is read from a model utilizing symmetry so ony data for, for example, positive z, is read. This data is
    then written to an odb where the model has instances for both +z and -z. To write the data to the -z instance,
    the ordering of the data must be changed which this function does

    :param data:    The original data array
    :param axis:    Axis to flip the data around. Currently only the z-axis is implemented
    :return:        A data array where the data is flipped that can be written to the other part of the odb file
    """
    if axis == 'z':
        for i in range(data.shape[0]/8):
            temp_data = np.copy(data[8*i:8*i+8])
            data[8*i:8*i+4] = temp_data[4:]
            data[8*i+4:8*i+8] = temp_data[:4]
    return data


def add_node_set(odb_file_name, node_set_name, node_labels, instance_name=None):
    """
    Function for creating a node set from node labels

    :param odb_file_name:   Name of the odb file where the node set will be created
    :param node_set_name:   Name of the node set
    :param node_labels:     A list of the node labels for the set
    :param instance_name:   Name of the instance where the set will be created. Must be provided if the model
                            contains several instances. Default is None which creates the set under
                            odb.rootAssembly.nodeSets
    :return:                Nothing
    """
    with OpenOdb(odb_file_name, read_only=False) as odb:
        if instance_name:
            base = odb.rootAssembly.instances[instance_name]
        else:
            if len(odb.rootAssembly.instances) == 1:
                base = odb.rootAssembly
            else:
                raise ValueError('odb has multiple instances, please specify an instance')
        if node_set_name not in base.nodeSets:
            base.NodeSetFromNodeLabels(name=node_set_name, nodeLabels=node_labels)


def add_element_set(odb_file_name, element_set_name, element_labels, instance_name=None):
    """
    Function for creating an element set in an odb given element labels

    :param odb_file_name:       Name of the odb file where the node set will be created
    :param element_set_name:    Name of the element set
    :param element_labels:      A list of the element labels for the set
    :param instance_name:       Name of the instance where the set will be created. Must be provided if the model
                                contains several instances. Default is None which creates the set under
                                odb.rootAssembly.nodeSets
    :return:                    Nothing
    """
    with OpenOdb(odb_file_name, read_only=False) as odb:
        if instance_name:
            base = odb.rootAssembly.instances[instance_name]
        else:
            if len(odb.rootAssembly.instances) == 1:
                base = odb.rootAssembly.instances[odb.rootAssembly.instances.keys()[0]]
            else:
                raise ValueError('odb has multiple instances, please specify an instance')
        if element_set_name not in base.elementSets:
            base.ElementSetFromElementLabels(name=element_set_name, elementLabels=element_labels)
