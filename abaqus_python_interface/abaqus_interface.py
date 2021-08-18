from collections import namedtuple

import os
import pickle
import pathlib
import subprocess

import numpy as np
from abaqus_interface.common import TemporaryDirectory


abaqus_python_directory = pathlib.Path(__file__).parents[1].absolute() / "abaqus_python_scripts"
print(abaqus_python_directory)

CoordinateSystem = namedtuple('CoordinateSystem', ['name', 'origin', 'point1', 'point2', 'system_type'])
cylindrical_system_z = CoordinateSystem(name='cylindrical', origin=(0., 0., 0.), point1=(1., 0., 0.),
                                        point2=(0., 1., 0.), system_type='CYLINDRICAL')


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
        if self.output is True:
            job = subprocess.Popen([self.shell_command, '-i', '-c', 'cd ' + str(directory) + ' &&' + command_string])
        else:
            f_null = open(os.devnull, 'w')
            job = subprocess.Popen([self.shell_command, '-i', '-c', 'cd ' + str(directory) + ' &&' + command_string],
                                   stdout=f_null, stderr=subprocess.STDOUT)
        job.wait()
        os.chdir(current_directory)

    def get_steps(self, odb_file_name):
        with TemporaryDirectory(odb_file_name) as work_directory:
            results_pickle_name = work_directory / 'results.pkl'
            self.run_command(self.abq + ' python get_steps.py ' + str(odb_file_name) + ' ' + str(results_pickle_name),
                             directory=abaqus_python_directory)
            with open(results_pickle_name, 'rb') as results_pickle:
                steps = pickle.load(results_pickle, encoding='latin1')
        return steps

    def get_frames(self, odb_file_name, step_name=-1):
        step_names = self.get_steps(odb_file_name)
        if step_name == -1:
            step_name = step_names[-1]
        elif step_name not in step_names:
            raise ValueError(f"The step name {step_name} is not present in the odb {odb_file_name}")
        with TemporaryDirectory(odb_file_name) as work_directory:
            results_pickle_name = work_directory / 'results.pkl'
            self.run_command(self.abq + ' python get_frames.py ' + str(odb_file_name) + ' ' + step_name + ' '
                             + str(results_pickle_name), directory=abaqus_python_directory)
            with open(results_pickle_name, 'rb') as results_pickle:
                frames = pickle.load(results_pickle, encoding='latin1')
        return frames

    def create_empty_odb_from_odb(self, new_odb_filename, odb_to_copy):
        self.run_command(self.abq + ' python create_empty_odb_from_odb.py ' + str(new_odb_filename) + ' '
                         + str(odb_to_copy), directory=abaqus_python_directory)

    def create_empty_odb_from_nodes_and_elements(self, odb_file_name, instances):
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

    def read_data_from_odb(self, field_id, odb_file_name, step_name=None, frame_number=-1, set_name='',
                           instance_name='', get_position_numbers=False, get_frame_value=False,
                           position='INTEGRATION_POINT', coordinate_system=None):
        with TemporaryDirectory(odb_file_name) as work_directory:
            parameter_pickle_name = work_directory / 'parameter_pickle.pkl'
            results_pickle_name = work_directory / 'results.pkl'
            if step_name is None:
                step_name = ''
            parameter_data = {'field_id': field_id, 'odb_file_name': str(odb_file_name), 'step_name': step_name,
                              'frame_number': frame_number, 'set_name': set_name, 'instance_name': instance_name,
                              'get_position_numbers': get_position_numbers, 'get_frame_value': get_frame_value,
                              'position': position}
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
        with TemporaryDirectory(odb_file_name) as work_directory:
            pickle_filename = work_directory / 'load_field_to_odb_pickle.pkl'
            data_filename = work_directory / 'field_data.npy'
            np.save(str(data_filename), field_data)
            if invariants is None:
                invariants = []
            with open(pickle_filename, 'wb') as pickle_file:
                pickle.dump({'field_id': str(field_id), 'odb_file': str(odb_file_name), 'step_name': str(step_name),
                             'instance_name': str(instance_name), 'set_name': str(set_name),
                             'step_description': str(step_description),
                             'frame_number': frame_number, 'frame_value': frame_value,
                             'field_description': str(field_description), 'position': str(position)},
                            pickle_file, protocol=2)

            self.run_command(self.abq + ' python write_data_to_odb.py ' + str(data_filename) + ' '
                             + str(pickle_filename), directory=abaqus_python_directory)

    def get_data_from_path(self, path_points, odb_filename, variable, component=None, step_name=None, frame_number=None,
                           output_position='ELEMENT_NODAL'):
        odb_filename = pathlib.Path(odb_filename)
        with TemporaryDirectory(odb_filename) as work_directory:
            parameter_pickle_name = work_directory / 'parameter_pickle.pkl'
            path_points_filename = work_directory / 'path_points.npy'
            data_filename = work_directory / 'path_data.npy'
            parameter_dict = {'odb_filename': str(odb_filename),
                              'variable': variable,
                              'path_points_filename': str(path_points_filename),
                              'data_filename': str(data_filename)}
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
            stress = self.get_data_from_path(path_points, odb_file_name, field_id, step_name=step_name,
                                             frame_number=frame_number, output_position=output_position,
                                             component=field_id + component)
            data[:, i] = stress
        return data
