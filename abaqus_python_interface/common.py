from __future__ import print_function
import os
import pathlib
import shutil

package_path = os.path.dirname(__file__)


class TemporaryDirectory:
    def __init__(self, name):
        self.name = name
        self.work_directory = None

    def __enter__(self):
        i = 0
        created = False
        while not created:
            work_directory_name = pathlib.Path(str(self.name.absolute()).replace('.', '_') + '_tempdir' + str(i))
            try:
                work_directory_name.mkdir(exist_ok=False)
            except FileExistsError:
                i += 1
            else:
                created = True
        self.work_directory = work_directory_name
        return work_directory_name

    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self.work_directory)
