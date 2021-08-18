from odbAccess import openOdb


class OpenOdb():
    def __init__(self, odb_file_name, read_only=True):
        self.filename = odb_file_name
        self.read_only = read_only
        self.odb = None

    def __enter__(self):
        self.odb = openOdb(self.filename, readOnly=self.read_only)
        return self.odb

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.read_only is False:
            self.odb.update()
            self.odb.save()
        self.odb.close()
