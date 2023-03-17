import pickle
import sys

from utilities import OpenOdb

def main():
    parameter_pickle_name = sys.argv[-1]

    with open(parameter_pickle_name, 'rb') as parameter_pickle:
        parameters = pickle.load(parameter_pickle)
    odb_file_name = str(parameters['odb_filename'])
    set_name = str(parameters['net_name'])
    set_type = str(parameters['set_type'])
    labels = parameters["labels"]
    instance_name = parameters.get("instance_name", None)
    with OpenOdb(odb_file_name, read_only=False) as odb:
        if instance_name is not None:
            base = odb.rootAssembly.instances[str(instance_name)]
        else:
            base = odb.rootAssembly
        if set_type == "node":
            base.NodeSetFromNodeLabels(name=set_name, nodeLabels=labels)
        elif set_type == "element":
            base.ElementSetFromElementLabels(name=set_name, nodeLabels=labels)
        else:
            raise ValueError("The argument set_type", set_type, " is invalid. It must either be nodes or elements")
        odb.update()
        odb.save()
        odb.close()


if __name__ == '__main__':
    main()
