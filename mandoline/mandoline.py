from collections import Iterable
import logging
import itertools
import json
import os

from requests import get as http_get, put as http_put
from boto.s3.connection import S3Connection

from cleaners import *


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
                    filename='mandoline.log')

# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('mandoline').addHandler(console)

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', None)


class FileCollection(object):
    def __init__(self, pattern, validators=[]):
        from glob import glob

        self.collection = glob(pattern)
        if validators:
            for file_validator in validators:
                for f in self.collection:
                    file_validator.test(f)

    @property
    def length(self):
        return len(self.collection)


class MandolineCleaner():
    """
    Contains a list of FieldCleaners
    """

    def __init__(self):
        self.fields = []
        self.logger = logging.getLogger("mandoline")
        self.rows = []
        self.inputrows = []
        self.input_filename = None
        self.output_filename = None


    # Tests

    def _requires_auth(self):
        assert not self.user is None and not self.api_key is None, "Needs authorization with authorize(username, api_key)"

    def _requires_files(self):
        assert not self.collection is None, "Needs files"
        assert self.collection.length > 0, "No files matched"

    def _requires_sliceboard(self):
        assert not self.sliceboard_obj is None, "Needs sliceboard"

    def _requires_cleaner(self):
        assert not self.cleaner is None, "Needs cleaner"

    def _requires_clean_rows(self):
        assert self.rows and len(self.rows) > 0

    def _requires_loaded_data(self):
        assert self.inputrows and len(self.inputrows) > 0

    # Helpers

    def _generate_field_metadata(self):
        flds = []
        for fld in self.fields:
            flds.append(fld.output_name)
            if isinstance(fld.extra_fields_to_save, basestring):
                flds.append(fld.extra_fields_to_save)
            elif isinstance(fld.extra_fields_to_save, Iterable):
                for f in fld.extra_fields_to_save:
                    flds.append(f)

        self.flds = flds
        self.fld_set = set(flds)

    # File loaders

    def files(self, pattern, *validators):
        assert isinstance(pattern, basestring), "Pattern must be a glob string"
        vals = [v for v in validators]
        self.collection = FileCollection(pattern, validators=vals)
        self.logger.info("Matched %d files" % self.collection.length)
        return self

    def set_fields(self, *fields):
        self.logger.info("Going to output %d fields" % (len(fields)))
        self.fields = list(fields)
        return self

    def clean(self):
        self._requires_files()

        for f in self.collection.collection:
            self.logger.info("Processing " + f)
            if f.endswith("xlsx"):
                self.loadxlsx(f)
                self._cleanrows()
            if f.endswith("csv"):
                self.loadcsv(f)
                self._cleanrows()
        return self

    def loadxlsx(self, f):
        """
        Take an excel file as an input to the cleaner.

        @param f: A file
        @return:
        """
        self._generate_field_metadata()
        self.input_filename = f

        from openpyxl import load_workbook

        self.logger.info("Loading as xlsx")
        wb = load_workbook(self.input_filename)
        sht = wb.get_sheet_by_name(wb.get_sheet_names()[0])
        header = sht.rows[0]
        rows = sht.rows[1:]

        self.inputrows = [dict(
            zip(map(lambda r: r.value, header), map(lambda r: r.value, row)))
                          for row in rows]
        self.logger.info("Found %d rows" % len(self.inputrows))
        return self

    def loadcsv(self, f):
        """

        """
        self._generate_field_metadata()
        self.input_filename = f

        reader = csv.DictReader(open(self.input_filename, 'r'))
        self.inputrows = list(reader)
        return self

    # Clean

    def _cleanrows(self):
        """
        Perform field cleaning on rows
        """
        self._generate_field_metadata()

        self.rows = []
        self.logger.info("Cleaning rows")

        for row in self.inputrows:
            for field in self.fields:
                field.clean(row)
                # delete excess keys
            for k in list(row.keys()):
                if k not in self.fld_set:
                    del row[k]
            self.rows.append(row)

        self.logger.info("Cleaned %d rows" % (len(self.rows)))
        return self


    def drop_field(self, fn):
        self.logger.info("Dropping field " + fn)
        for idx, fld in enumerate(self.fields):
            if fld.field_name == fn:
                self.fields.pop(idx)
                break
        self._generate_field_metadata()
        return self


    def process(self, fn):
        """ Ad hoc processing
        """

        self.logger.info(
            "Processing, performing arbitrary actions on the clean rows")
        self._generate_field_metadata()
        fn(self)
        return self


    def aggregate(self, *sum_fields):
        self._requires_clean_rows()

        self.logger.info(
            "Aggregating, initial row count is %d" % (len(self.rows)))
        self._generate_field_metadata()
        key_fields = [f for f in self.flds if f not in sum_fields]
        aggr_fields = [f for f in self.flds if f in sum_fields]

        d = {}
        for row in self.rows:
            key = tuple(row[k] for k in key_fields)
            if key not in d:
                d[key] = [0 for f in aggr_fields]
            v = d[key]
            for idx, f in enumerate(aggr_fields):
                v[idx] += row[f]

        self.rows = []
        for keys in d.keys():
            row = dict(itertools.izip(key_fields, keys))
            row.update(dict(itertools.izip(aggr_fields, d[keys])))
            self.rows.append(row)

        self.logger.info(
            "Aggregating, after aggregation row count is %d" % (len(self.rows)))
        return self

    # Outputs

    def to_csv(self, fn=None):
        self._requires_clean_rows()

        if fn is None:
            self.output_filename = self.input_filename + '.clean'
        else:
            self.output_filename = fn

        writer = DictUnicodeWriter(open(self.output_filename, 'w'), self.flds,
                                   extrasaction='ignore')

        writer.writeheader()
        for row in self.rows:
            writer.writerow(row)

        self.logger.info("Wrote csv file %s" % (self.output_filename))
        return self

    def to_json(self, fn=None):
        self._requires_clean_rows()

        if fn is None:
            self.output_filename = self.input_filename + '.clean.json'
        else:
            path, _ = os.path.split(os.path.abspath(self.input_filename))
            self.output_filename = os.path.join(path, fn)

        json.dump({"rows": self.rows}, open(self.output_filename, 'wb'),
                  indent=0)
        self.logger.info("Wrote json file %s" % (self.output_filename))
        return self

    def refine_fieldnames(self):
        self.logger.info(
            "Converting fieldnames to match refine (lowercase, no spaces)")
        self._requires_clean_rows()

        new_rows = []
        field_map = {}
        for k in self.rows[0].keys():
            field_map[k] = k.lower().replace(' ', '_')
        for row in self.rows:
            new_row = {}
            for k, newk in field_map.items():
                new_row[newk] = row[k]
            new_rows.append(new_row)
        self.rows = new_rows
        return self

    def to_s3_rows_cache(self, fn=None, randomize=False):
        """
        Send output to S3
        """
        self._requires_clean_rows()

        from random import choice
        from string import letters, digits
        # send output to S3

        assert AWS_ACCESS_KEY_ID is not None, "Needs environment variable AWS_ACCESS_KEY_ID to be set"
        assert AWS_SECRET_ACCESS_KEY is not None, "Needs environment variable AWS_SECRET_ACCESS_KEY to be set"

        if self.output_filename and not self.output_file.endswith('.json'):
            raise Exception("File must be converted with to_json")
        else:
            self.logger.info("Generating random filename for s3")
            path, fn = os.path.split(self.output_filename)

            if randomize:
                s3_file_name = "{0}_{1}".format(
                    "".join((choice(letters + digits) for _ in xrange(10))),
                    fn)
            else:
                s3_file_name = fn

            self.logger.info("s3 file name: %s" % (s3_file_name))

            try:
                conn = S3Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
                bucket = conn.create_bucket('slice-rows-cache')
                k = bucket.new_key(s3_file_name)
                self.logger.info("Created new s3 file")
            except Exception as e:
                raise Exception(
                    "Could not open bucket / create new key {0} {1}".format(
                        s3_file_name, e))
            k.content_type = 'application/json'

            content = open(self.output_filename, 'r').read()

            try:
                k.set_contents_from_string(content)
                self.logger.info("Write %d bytes to new file" % (len(content)))
            except Exception as e:
                raise Exception("Could not write file to S3 {0}".format(e))

            self.s3_file_name = s3_file_name


class MandolineMasher(object):
    """
    Concatenates files together
    """

    def __init__(self):
        self.logger = logging.getLogger("mandoline.masher")


    def files(self, pattern):
        assert isinstance(pattern, basestring), "Pattern must be a glob string"
        self.collection = FileCollection(pattern)
        self.logger.info("Matched %d files" % self.collection.length)
        return self

    def to_csv(self, output_filename, delete_headers=True):
        """
        Concatenates a bunch of files together
        """
        outf = open(output_filename, 'wb')
        first = True
        for f in self.collection.collection:
            lines = open(f).readlines()
            if first:
                outf.writelines(lines)
                self.logger.info(
                    "Wrote %d lines (including header) from %s to %s" % (
                        len(lines), f, output_filename))
            else:
                if delete_headers:
                    lines = lines[1:]
                    outf.writelines(lines)
                    self.logger.info("Wrote %d lines from %s to %s" % (
                        len(lines), f, output_filename))
                else:
                    outf.writelines(lines)
                    self.logger.info(
                        "Wrote %d lines (including header) from %s to %s" % (
                            len(lines), f, output_filename))
            first = False
        self.logger.info("Complete")
        outf.close()


class MandolineSlice(object):
    """
    Talks to slice and changes slice objects

    MandolineSlice('staging.juiceslice.com').sliceboard(3183).duplicate().rename_old("Copy of {sliceboard.name}")

    """

    def __init__(self, server_url=None):
        self.user = None
        self.api_key = None
        self.server = server_url
        self.sliceboard_id = None
        self.sliceboard_obj = None
        self.collection = None
        self.logger = logging.getLogger("mandoline.slice")

    # Tests

    def _requires_auth(self):
        assert not self.user is None and not self.api_key is None, "Needs authorization with authorize(username, api_key)"

    def _requires_files(self):
        assert not self.collection is None, "Needs files"
        assert self.collection.length > 0, "No files matched"

    def _requires_sliceboard(self):
        assert not self.sliceboard_obj is None, "Needs sliceboard"

    # Helpers

    @property
    def auth_params(self):
        self._requires_auth()
        return "?api_key={0.api_key}&username={0.user}".format(self)

    @property
    def sliceboard_detail_uri(self):
        return "http://{0.server}/api/v1/sliceboard/{0.sliceboard_id}".format(
            self)

    @property
    def sliceboard_list_uri(self):
        return "http://{0.server}/api/v1/sliceboard/".format(self)

    # General commands

    def authenticate(self, user, api_key):
        """ Authenticate """
        self.user = user
        self.api_key = api_key
        return self

    # Commands related to slice

    def _show_sliceboard(self, sb, full=False):
        print "{id:4d} {title}".format(**sb)
        if full:
            print "\tviewers: {viewers}".format(**sb)
            print "\teditors: {editors}".format(**sb)
            print "\tslices: "
            for s in sb['thinSlices']:
                print "\t\t({type}) {title}".format(**s)
            print


    def show_sliceboards(self, full=False):
        response = http_get(self.sliceboard_list_uri + self.auth_params,
                            stream=False)
        for sb in response.json()["objects"]:
            self._show_sliceboard(sb, full)
        return self

    def show_sliceboard(self, sliceboard_id, full=True):
        self.sliceboard(sliceboard_id)
        self._show_sliceboard(self.sliceboard_obj, full)
        return self


    def sliceboard(self, sliceboard_id):
        """
        Get a sliceboard object
        """
        self.sliceboard_id = sliceboard_id
        response = http_get(self.sliceboard_detail_uri + self.auth_params,
                            stream=False)
        self.sliceboard_obj = response.json()
        self.logger.info(str(self.sliceboard_obj['title']))
        assert response.status_code == 200
        return self
        # print self.sliceboard_obj

    def title(self, new_title="Untitled"):
        """
        Change the title of the sliceboard

        You can use the sliceboard to build the title. For instance

        sliceboard(100).title("Copy of {0[title]}") will rename from
        "Untitled" to "Copy of Untitled"

        """
        assert self.sliceboard_obj is not None
        assert new_title is not None

        headers = {"content-type": "application/json; charset=utf8"}
        put_url = self.sliceboard_detail_uri + self.auth_params
        data = {"title": new_title.format(self.sliceboard_obj)}
        print data
        response = http_put(put_url, data=json.dumps(data), headers=headers)
        print '-'*80
        print put_url
        print json.dumps(data)
        print headers
        print '-'*80
        print "stat"
        print response.status_code
        assert response.status_code == 202
        return self

    def duplicate(self):
        """
        Duplicate the sliceboard, after duplication
        """
        if self.sliceboard_obj is None:
            raise Exception("Need a sliceboard")
        duplicate_url = "{0.sliceboard_detail_uri}/duplicate{0.auth_params}".format(
            self)
        response = http_get(duplicate_url, stream=False)
        self.duplicate_obj = response.json()

        return self

    def replace_data(self, filename=None):
        """
        Replace the data attached to this slice with the rows_cache specified

        """
        self._requires_sliceboard()

        assert filename is not None

        headers = {"content-type": "application/json; charset=utf8"}
        put_url = "http://" + self.server + self.sliceboard_obj[
            'data'] + '/set_rows_cache' + self.auth_params
        data = {'s3_rows_cache': filename}
        self.logger.info('Replacing data: ' + put_url)
        response = http_put(put_url, data=json.dumps(data), headers=headers)
        self.logger.info(
            'Replacing data: status code ' + str(response.status_code))
        return self

