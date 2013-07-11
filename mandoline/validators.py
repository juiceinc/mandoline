"""
Validators test to make sure a file matches
"""

import logging

logger = logging.getLogger("mandoline.validator")


class FileValidator(object):
    def __init__(self):
        self.description = "File validator"

    def test(self, f):
        """
        Test if the file is valid

        @param f a filename
        """
        self.log(f)


class SizeValidator(FileValidator):
    def __init__(self, length):
        self.length = length
        self.description = "File length is greater than {len}".format(
            len=length)

    def test(self, f):
        content = open(f, 'r').read()
        assert len(content) >= self.length
        logger.debug(f + " passed " + self.description)


class HeaderValidator(FileValidator):
    """
    Validate that the header matches
    """

    def __init__(self, header):
        self.header = header
        self.description = "Header matches \"{header}\"...".format(
            header=self.header[:40])

    def test(self, f):
        lines = open(f, 'r').readlines()
        file_header = lines[0].rstrip('\n')
        assert file_header == self.header
        logger.debug(f + " passed " + self.description)


