import pathlib
import unittest


class TestTemporaryDirectory(unittest.TestCase):
    def test_create_tempdir(self):
        from abaqus_python_interface.common import TemporaryDirectory
        with TemporaryDirectory(pathlib.Path("test_filename.odb")) as temp_dir:
            self.assertTrue(temp_dir.exists())

    def test_create_additional_tempdir(self):
        from abaqus_python_interface.common import TemporaryDirectory
        with TemporaryDirectory(pathlib.Path("test_filename.odb")):
            with TemporaryDirectory(pathlib.Path("test_filename.odb")) as temp_dir2:
                self.assertTrue(temp_dir2.exists())

    def test_cleanup(self):
        from abaqus_python_interface.common import TemporaryDirectory
        with TemporaryDirectory(pathlib.Path("test_filename.odb")) as temp_dir:
            try:
                raise ValueError("Just to raise something")
            except ValueError:
                pass
        self.assertFalse(temp_dir.exists())
