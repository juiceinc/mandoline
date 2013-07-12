import glob
from nose.tools import with_setup
import os
from mandoline import *
from mandoline import FieldCleaner as _

# def TestCleaner(TestCase):
#     def setup(self):
#         pass
#
#     def teardown(self):
#         pass
#
#     def test_cleaner(self):
#         cleaner = MandolineCleaner()
#         cleaner.files("Sample.xlsx").set_fields(_('Organization'),
#                             _('Facility'),
#                             _('Department'),
#                             _('Job Category'),
#                             _('Course'),
#                             _('Date', Date()),
#                             _('Completion Count', Int()),
#                             _('City'),
#                             _('State'),
#                             _('Zip')).clean().refine_fieldnames().to_json()
#
#     def testit(self):
#         assert 1== 1

def datapath(fn):
    """ Returns a filename in the data directory
    """
    full_path = os.path.realpath(__file__)
    path, file = os.path.split(full_path)
    return os.path.join(path, "data", fn)


def testpath(fn):
    pass

def setup():
    """ Remove all files from the data directory except for our test files
    """
    full_path = os.path.realpath(__file__)
    path, file = os.path.split(full_path)
    for fn in glob.glob(os.path.join(path, "data", "*")):
        p, f = os.path.split(fn)
        if f not in ("Sample.csv", "Sample.xlsx"):
            os.remove(fn)


def teardown():
    pass


@with_setup(setup, teardown)
def test():
    full_path = os.path.realpath(__file__)
    path, file = os.path.split(full_path)
    fn = os.path.join(path, "data", "Sample.xlsx")

    cleaner = MandolineCleaner()
    cleaner.files(fn).set_fields(_('Organization'),
                        _('Facility'),
                        _('Department'),
                        _('Job Category'),
                        _('Course'),
                        _('Date', Date()),
                        _('Completion Count', Int()),
                        _('City'),
                        _('State'),
                        _('Zip')).clean().refine_fieldnames().to_json("output.json")
    try:
        print datapath("output.json")
        # open(datapath("output.json"))
    except IOError:
        assert 1 == 0, "File does not exist"

