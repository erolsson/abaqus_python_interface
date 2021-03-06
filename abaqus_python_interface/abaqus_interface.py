from collections import namedtuple

import os
import pickle
import pathlib
import subprocess
import time

import numpy as np
from abaqus_python_interface.common import TemporaryDirectory


abaqus_python_directory = pathlib.Path(__file__).parents[1].absolute() / "abaqus_python_scripts"

CoordinateSystem = namedtuple('CoordinateSystem', ['name', 'origin', 'point1', 'point2', 'system_type'])
cylindrical_system_z = CoordinateSystem(name='cylindrical', origin=(0., 0., 0.), point1=(1., 0., 0.),
                                        point2=(0., 1., 0.), system_type='CYLINDRICAL')


class OdbReadingError(KeyError):
    pass


class OdbWritingError(ValueError):
    pass


class OdbInstance:
    def __init__(self, name, input_file_data):
        self.data = {
            'instance_name': name,
            'elements': {},
            'node_sets': input_file_data.set_data['nset'],
            'element_sets': input_file_data.set_data['elset']
        }
        nodes = []
        for n in input_file_data.nodal_data:
            node_data_list = [int(n[0])]
            node_data_list.extend([float(coord) for coord in n[1:]])
            nodes.append(node_data_list)
        self.data['nodes'] = nodes
        for element_type, element_data in input_file_data.elements.items():
            pass
            self.data['elements'][element_type] = element_data.tolist()


def check_odb_file(odb_file_name, exists=True):
    odb_path = pathlib.Path(odb_file_name)
    if not odb_path.is_file() and exists:
        raise OdbReadingError("The odb file " + str(odb_file_name) + " does not exist")
    return odb_path


class ABQInterface:
    def __init__(self, abq_command, shell=None, output=False):
        self.abq = abq_command
        if shell is None:
            shell = '/bin/bash'
        # ToDo: Update shell command for windows systems
        self.shell_command = shell
        self.output = output

    def run_command(self, command_string, directory=None):
        current_directory = os.getcwd()
        if directory is not None:
            os.chdir(directory)
        stdout = None
        stderr = None
        if self.output is False:
            stdout = open(os.devnull, 'w')
            stderr = subprocess.STDOUT
        job = subprocess.run([self.shell_command, '-ic', "cd " + str(directory) + " && " +  command_string + " && "
                              + "exit"],
                               stderr=stderr, stdout=stdout)
        os.chdir(current_directory)

    def get_steps(self, odb_file_name):
        return list(self.get_odb_as_dict(odb_file_name)["steps"].keys())

    def get_frames(self, odb_file_name, step_name=-1):
        steps = self.get_odb_as_dict(odb_file_name)["steps"]
        if len(steps) == 0.:
            return []
        if step_name == -1:
            step_name = list(steps.keys())[-1]
        elif step_name not in steps:
            raise OdbReadingError(f"The step name {step_name} is not present in the odb {odb_file_name}")
        return list(range(len(steps[step_name])))

    def get_odb_as_dict(self, odb_file_name):
        odb_file_name = check_odb_file(odb_file_name)
        with TemporaryDirectory(odb_file_name) as work_directory:
            results_pickle_name = work_directory / 'results.pkl'
            self.run_command(self.abq + ' python odb_as_dict.py ' + str(odb_file_name) + ' '
                             + str(results_pickle_name), directory=abaqus_python_directory)
            with open(results_pickle_name, 'rb') as results_pickle:
                odb_dict = pickle.load(results_pickle, encoding='latin1')
        return odb_dict

    def create_empty_odb_from_odb(self, new_odb_filename, odb_to_copy):
        new_odb_filename = pathlib.Path(new_odb_filename)
        dir_name = new_odb_filename.absolute().parents[0]
        dir_name.mkdir(exist_ok=True)
        self.run_command(self.abq + ' python create_empty_odb_from_odb.py ' + str(new_odb_filename) + ' '
                         + str(odb_to_copy), directory=abaqus_python_directory)

    def create_empty_odb_from_nodes_and_elements(self, odb_file_name, instances):
        odb_file_name = check_odb_file(odb_file_name, exists=False)
        instances = [instance.data for instance in instances]
        data_for_creating_odb = {
            'odb_file_name': str(odb_file_name),
            'instance_data': instances
        }
        with TemporaryDirectory(odb_file_name) as work_directory:
            parameter_pickle_name = work_directory / 'parameter_pickle.pkl'
            with open(parameter_pickle_name, 'wb') as pickle_file:
                pickle.dump(data_for_creating_odb, pickle_file, protocol=2)
            self.run_command(self.abq + ' python create_empty_odb_from_data.py ' + str(parameter_pickle_name),
                             directory=abaqus_python_directory)

    def validate_field(self, odb_file_name, step_name, frame_number, field_id=None):
        odb_dict = self.get_odb_as_dict(odb_file_name)
        odb_steps = list(odb_dict["steps"].keys())
        if step_name is None:
            step_name =odb_steps[-1]
        elif step_name not in odb_dict["steps"]:
            raise OdbReadingError("The step " + step_name + " does not exist in the odb file " + str(odb_file_name))

        odb_frames = list(odb_dict["steps"][step_name].keys())
        if frame_number == -1:
            frame_number = odb_frames[-1]
        if frame_number not in odb_dict["steps"][step_name]:
            raise OdbReadingError("The frame number " + str(frame_number) + " does not exist in the step " + step_name +
                                  " in the odb file " + str(odb_file_name))
        if field_id is not None and field_id not in odb_dict["steps"][step_name][frame_number]["fieldOutputs"]:
            raise OdbReadingError("The field " + field_id + " is not present in the frame " + str(frame_number)
                                  + " in step " + step_name + " in the odb file " + str(odb_file_name))
        return step_name, frame_number

    def validate_set(self, odb_file_name, instance_name, set_name, position='INTEGRATION_POINT'):
        odb_dict = self.get_odb_as_dict(odb_file_name)
        set_type = "elementSets"
        if position == "NODAL":
            set_type = "nodeSets"
        if not instance_name:
            if set_name in odb_dict["rootAssembly"][set_type]:
                return None, set_name
            if len(odb_dict["rootAssembly"]["instances"]) == 1:
                instance_name = next(iter(odb_dict["rootAssembly"]["instances"]))
                if not set_name or set_name in odb_dict["rootAssembly"]["instances"][instance_name][set_type]:
                    return instance_name, set_name
            raise OdbReadingError(
                "The " + set_type[:-1] + " " + set_name + " is not present in the rootAssembly of the  odb "
                + str(odb_file_name) + " or if there is several instances in the odb file, specify an instance"
            )
        else:
            if instance_name not in odb_dict["rootAssembly"]["instances"]:
                raise OdbReadingError(
                    "The instance " + instance_name + " is not present in the odb " + str(odb_file_name)
                )
            if set_name and set_name not in odb_dict["rootAssembly"]["instances"][instance_name][set_type]:
                raise OdbReadingError(
                    "The " + set_type[:-1] + " " + set_name + " is not present in the instance " + instance_name
                    + " in the odb file " + str(odb_file_name)
                )
        return instance_name, set_name

    def read_data_from_odb(self, field_id, odb_file_name, step_name=None, frame_number=-1, set_name='',
                           instance_name='', get_position_numbers=False, get_frame_value=False,
                           position='INTEGRATION_POINT', coordinate_system=None):
        odb_file_name = check_odb_file(odb_file_name)
        step_name, frame_number = self.validate_field(odb_file_name, step_name, frame_number, field_id)
        instance_name, set_name = self.validate_set(odb_file_name, instance_name, set_name)

        with TemporaryDirectory(odb_file_name) as work_directory:
            parameter_pickle_name = work_directory / 'parameter_pickle.pkl'
            results_pickle_name = work_directory / 'results.pkl'
            parameter_data = {
                'field_id': field_id,
                'odb_file_name': str(odb_file_name),
                'step_name': step_name,
                'frame_number': frame_number,
                'set_name': set_name,
                'instance_name': instance_name,
                'get_position_numbers': get_position_numbers,
                'get_frame_value': get_frame_value,
                'position': position
            }

            if coordinate_system:
                parameter_data['coordinate_system'] = coordinate_system._asdict()
            with open(parameter_pickle_name, 'wb') as pickle_file:
                pickle.dump(parameter_data, pickle_file, protocol=2)
            self.run_command(self.abq + ' python read_data_from_odb.py ' + str(parameter_pickle_name) + ' '
                             + str(results_pickle_name), directory=abaqus_python_directory)
            with open(results_pickle_name, 'rb') as results_pickle:
                data = pickle.load(results_pickle, encoding='latin1')

        if not get_position_numbers and not get_frame_value:
            return data['data']
        elif not get_position_numbers:
            return data['data'], data['frame_value']
        elif not get_frame_value:
            return data['data'], data['node_labels'], data['element_labels']
        else:
            return data['data'], data['frame_value'], data['node_labels'], data['element_labels']

    def write_data_to_odb(self, field_data, field_id, odb_file_name, step_name, instance_name='', set_name='',
                          step_description='', frame_number=None, frame_value=None, field_description='',
                          position='INTEGRATION_POINT', invariants=None):
        odb_file_name = check_odb_file(odb_file_name)
        instance_name, set_name = self.validate_set(odb_file_name, instance_name, set_name)
        with TemporaryDirectory(odb_file_name) as work_directory:
            pickle_filename = work_directory / 'load_field_to_odb_pickle.pkl'
            data_filename = work_directory / 'field_data.npy'
            np.save(str(data_filename), field_data)
            if invariants is None:
                invariants = []
            with open(pickle_filename, 'wb') as pickle_file:
                pickle.dump({
                    'field_id': field_id,
                    'odb_file': str(odb_file_name),
                    'step_name': step_name,
                    'instance_name': instance_name,
                    'set_name': set_name,
                    'step_description': step_description,
                    'frame_number': frame_number,
                    'frame_value': frame_value,
                    'field_description': field_description,
                    'position': position
                },
                        pickle_file, protocol=2)

            self.run_command(self.abq + ' python write_data_to_odb.py ' + str(data_filename) + ' '
                             + str(pickle_filename), directory=abaqus_python_directory)
            with open(pickle_filename, 'rb') as pickle_file:
                return_dict = pickle.load(pickle_file)
            if "ERROR" in return_dict:
                raise OdbWritingError(" ".join(return_dict["ERROR"]))

    def get_data_from_path(self, odb_file_name, path_points, variable, component=None, step_name=None, frame_number=None,
                           output_position='ELEMENT_NODAL'):
        odb_file_name = check_odb_file(odb_file_name)
        with TemporaryDirectory(odb_file_name) as work_directory:
            parameter_pickle_name = work_directory / 'parameter_pickle.pkl'
            path_points_filename = work_directory / 'path_points.npy'
            data_filename = work_directory / 'path_data.npy'
            parameter_dict = {
                'odb_filename': str(odb_file_name),
                'variable': variable,
                'path_points_filename': str(path_points_filename),
                'data_filename': str(data_filename)
            }

            if component is not None:
                parameter_dict['component'] = component
            if step_name is not None:
                parameter_dict['step_name'] = step_name
            if frame_number is not None:
                parameter_dict['frame_number'] = frame_number
            parameter_dict['output_position'] = output_position

            with open(parameter_pickle_name, 'wb') as pickle_file:
                pickle.dump(parameter_dict, pickle_file, protocol=2)
            if not isinstance(path_points, np.ndarray):
                path_points = np.array(path_points)
            np.save(path_points_filename, path_points)
            self.run_command(self.abq + ' viewer noGUI=write_data_along_path.py -- ' + str(parameter_pickle_name),
                             directory=abaqus_python_directory)
            data = np.unique(np.load(data_filename), axis=0)
            _, idx = np.unique(data[:, 0], return_index=True)
            return data[idx, 1]

    def get_tensor_from_path(self, odb_file_name, path_points, field_id, step_name=None, frame_number=None,
                             components=('11', '22', '33', '12', '13', '23'), output_position='INTEGRATION_POINT'):
        data = np.zeros((path_points.shape[0], len(components)))
        for i, component in enumerate(components):
            stress = self.get_data_from_path(
                odb_file_name, path_points, field_id, step_name=step_name, frame_number=frame_number,
                output_position=output_position, component=field_id + component)
            data[:, i] = stress
        return data

    def get_element_data(self, odb_file_name, element_set=None, instance_name=None):
        """
        :param odb_file_name:   Name of the odb file
        :param element_set:     Optional: Name of the element set. If omitted all elements in the instance or the model
                                is used
        :param instance_name:   Optional: Name of the instance. If omitted and the model contains just one instance and,
                                no elements on the rootAssembly that one is used.
        :return:                A dict of the type {element_type: {element_number: element_data}}
                                where element data is an array with  the nodal coordinates for the element accordning
                                to the standard ordering of nodes
        """
        odb_file_name = check_odb_file(odb_file_name)
        instance_name, element_set = self.validate_set(odb_file_name, instance_name, element_set)
        with TemporaryDirectory(odb_file_name) as work_directory:
            parameter_pickle_name = work_directory / 'parameter_pickle.pkl'
            results_pickle_name = work_directory /'results.pkl'
            parameter_dict = {
                'odb_filename': str(odb_file_name),
            }
            if element_set:
                parameter_dict["element_set"] = element_set
            if instance_name:
                parameter_dict["instance_name"] = instance_name
            with open(parameter_pickle_name, 'wb') as pickle_file:
                pickle.dump(parameter_dict, pickle_file, protocol=2)
            self.run_command((self.abq + ' viewer noGUI=write_element_data.py -- ' + str(parameter_pickle_name) + " "
                              + str(results_pickle_name)), directory=abaqus_python_directory)
            with open(results_pickle_name, 'rb') as results_pickle:
                return pickle.load(results_pickle, encoding="latin1")

if __name__ == '__main__':
    abq = ABQInterface('abq2018')
    abq.read_data_from_odb('S', 'test.odb')
