# coding: utf-8
import csv
import cStringIO
import codecs
import logging


logger = logging.getLogger("mandoline.cleaners")


class DictUnicodeWriter(object):
    def __init__(self, f, fieldnames, dialect=csv.excel, encoding="utf-8",
                 **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.DictWriter(self.queue, fieldnames, dialect=dialect,
                                     **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, D):
        self.writer.writerow(
            {k: unicode(v).encode("utf-8") for k, v in D.items()})
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for D in rows:
            self.writerow(D)

    def writeheader(self):
        self.writer.writeheader()


class FieldRowCleaner():
    pass


class Rename(FieldRowCleaner):
    """
    Rename a field to a new name
    Rename("a", "b")
    { "a": 1 }  => { "b": 1 }

    """

    def __init__(self, from_name, to_name):
        self.from_name = from_name
        self.to_name = to_name

    def clean(self, d, from_name, to_name):
        d[to_name] = d[from_name]


class CleanWith(FieldRowCleaner):
    """
    Takes a cleaning function with signature

    clean(row, fieldname) where

    row is a dictionary containing the row being cleaned
    fieldname is the fieldname being cleaned

    The result of the clean function should be to modify row[fieldname]
    """

    def __init__(self, clean):
        self.clean_func = clean

    def clean(self, d, fn):
        self.clean_func(d, fn)


class Lookup(FieldRowCleaner):
    """
    Use a lookup table to determine a new value for a field

    If default is None, then if the value isn't found in the lookup
    then use the original value

    Lookup("a", { 1: 2}, 4)

    { "a": 1 }  => { "a": 2 }
    { "a": 2 }  => { "a": 4 } # gets the default value

    """

    def __init__(self, lookup, default=None):
        self.lookup = lookup
        self.default = default

    def clean(self, d, fn):
        if self.default is None:
            d[fn] = self.lookup.get(d[fn], d[fn])
        else:
            d[fn] = self.lookup.get(d[fn], self.default)


class StateAbbrevLookup(Lookup):
    def __init__(self, default=None):
        self.default = default
        self.lookup = {
            "DISTRICT OF COLUMBIA": "DC",
            "ALABAMA": "AL",
            "ALASKA": "AK",
            "ARIZONA": "AZ",
            "ARKANSAS": "AR",
            "CALIFORNIA": "CA",
            "COLORADO": "CO",
            "CONNECTICUT": "CT",
            "DELAWARE": "DE",
            "FLORIDA": "FL",
            "GEORGIA": "GA",
            "HAWAII": "HI",
            "IDAHO": "ID",
            "ILLINOIS": "IL",
            "INDIANA": "IN",
            "IOWA": "IA",
            "KANSAS": "KS",
            "KENTUCKY": "KY",
            "LOUISIANA": "LA",
            "MAINE": "ME",
            "MARYLAND": "MD",
            "MASSACHUSETTS": "MA",
            "MICHIGAN": "MI",
            "MINNESOTA": "MN",
            "MISSISSIPPI": "MS",
            "MISSOURI": "MO",
            "MONTANA": "MT",
            "NEBRASKA": "NE",
            "NEVADA": "NV",
            "NEW HAMPSHIRE": "NH",
            "NEW JERSEY": "NJ",
            "NEW MEXICO": "NM",
            "NEW YORK": "NY",
            "NORTH CAROLINA": "NC",
            "NORTH DAKOTA": "ND",
            "OHIO": "OH",
            "OKLAHOMA": "OK",
            "OREGON": "OR",
            "PENNSYLVANIA": "PA",
            "RHODE ISLAND": "RI",
            "SOUTH CAROLINA": "SC",
            "SOUTH DAKOTA": "SD",
            "TENNESSEE": "TN",
            "TEXAS": "TX",
            "UTAH": "UT",
            "VERMONT": "VT",
            "VIRGINIA": "VA",
            "WASHINGTON": "WA",
            "WEST VIRGINIA": "WV",
            "WISCONSIN": "WI",
            "WYOMING": "WY",
        }

    def clean(self, d, fn):
        if self.default is None:
            d[fn] = self.lookup.get(d[fn].upper(), d[fn])
        else:
            d[fn] = self.lookup.get(d[fn].upper(), self.default)


class Int(FieldRowCleaner):
    """
    Convert a value to an integer, optionally taking a default value

    Int("a", 0)
    { "a": "1" } => { "a": 1 }
    { "a": "fred" } => { "a": 0 }

    """

    def __init__(self, default=0):
        self.default = default

    def clean(self, d, fn):
        s = str(d[fn])
        if s.isdigit():
            d[fn] = int(s)
        else:
            assert self.default is not None, "Failed to parse an integer without a default"
            d[fn] = self.default


class Date(FieldRowCleaner):
    """
    Convert a value to an integer, optionally taking a default value

    Int("a", 0)
    { "a": "1" } => { "a": 1 }
    { "a": "fred" } => { "a": 0 }

    """

    def __init__(self, format="%m-%d-%Y"):
        self.format = format

    def clean(self, d, fn):
        from datetime import datetime
        from time import mktime

        try:
            dt = datetime.strptime(d[fn], self.format)
            # multiply by 1000 to convert to ms
            d[fn] = int(mktime(dt.timetuple())) * 1000
        except:
            d[fn] = None


class FieldCleaner():
    def __init__(self, field_name, *cleaners, **kwargs):
        extra_fields_to_save = kwargs.get('extra_fields_to_save', None)
        self.field_name = field_name
        self.output_name = field_name
        self.extra_fields_to_save = extra_fields_to_save
        self.cleaners = list(cleaners)

        if '=>' in field_name:
            self.field_name, self.output_name = field_name.split('=>')
            self.cleaners.append(Rename(self.field_name, self.output_name))

    def clean(self, d):
        for cleaner in self.cleaners:
            if isinstance(cleaner, Rename):
                cleaner.clean(d, self.field_name, self.output_name)
            else:
                cleaner.clean(d, self.field_name)

