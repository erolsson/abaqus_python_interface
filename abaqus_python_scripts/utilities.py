from __future__ import print_function
import os

from odbAccess import openOdb



class OpenOdb:
    def __init__(self, odb_file_name, read_only=True):
        self.filename = odb_file_name
        self.read_only = read_only
        self.odb = None

    def __enter__(self):
        lock_file = os.path.splitext(self.filename)[0] + ".lck"
        if not self.read_only and os.path.isfile(lock_file):
            print("Lock file " + lock_file + " detected. The odb-file will be opened when the lock file is removed")
            while os.path.isfile(lock_file):
                pass
        self.odb = openOdb(self.filename, readOnly=self.read_only)
        return self.odb

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.read_only is False:
            self.odb.update()
            self.odb.save()
        self.odb.close()
