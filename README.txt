===========
Mandoline
===========

Mandoline is a tool to prepare data files and attach data to
to Juice Slice sliceboards.




The MandolineCleaner
===========

The MandolineCleaner has five steps


Step 1: files: Which files you want to clean?
-----------

With the `files` step you give Mandoline a pattern that matches the files
you want to process. For instance, to process all xlsx files, you say

  files("*.xlsx")

You can optionally give Mandoline a list of validators that will check the files
to make sure they look like what you expect. There are two validators:

  SizeValidator(n) checks that file size is greater than n bytes
  HeaderValidator(header) checks that the first row of the file matches header

For instance,:

  files("*.xlsx", SizeValidator(5000))

checks that files are at least 5000 bytes in size. You can also use

  files("*.csv", SizeValidator(5000), HeaderValidator("date,age,zip"))

checks that the file is over 5000 bytes in size and has the header "date,age,zip".


Step 2: Setting fields
-----------

Mandoline only reads the fields from the input that you are interested in.
Set them with

  set_fields(a list of fields)

Each of the list of fields should look like this

  _({field name})

If you want to convert the data from strings, you can use

  _({field name}, cleaners)

Mandoline has these cleaners built in

  Lookup: Lookup takes a dictionary and will
  StateAbbrevLookup: Performs a lookup from full state names to two digit abbreviations



Step 3: Cleaning
-----------

The clean step is created by calling `.clean()` on Mandoline. This will read
the files in and keep only the fields that you listed in `set_fields`


Step 4: Post cleaning (optional)
-----------

After the data has been cleaned

  refine_fieldnames: Converts all the field names to the names they likely
    have in slice (lowercase and all spaces converted to underscores)
  process(function): Does arbitrary "stuff" to the cleaned data
  drop_field(field_name): Drops a field from the output.

Step 5: Output
-----------

To get your data out of Mandoline, use one of the following.

  to_json(): Writes data to a json file
  to_csv(): Writes data to a csv file.
  to_s3_rows_cache(): Pushes data up the slice's S3 storage. This is required
    if you want to replace data on a sliceboard.
    This requires that you've called to_json() first.
    There is an optional parameter randomize that will prefix the filename with
    10 random characters which is good if you don't want to overwrite data
    that is already on slice. To use this call `to_s3_rows_cache(randomize=True)`.


