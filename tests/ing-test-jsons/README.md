Note: The files in this directory are also used for tests of Docker images (in particular ingestion script).

## Timestamps
For some tests, JSON files with current Epoch timestamp value in the `timestamp` field are required. The actual input files are prepared from the templates just before running the actual tests. The script is launched from the `docker-compose.yaml` file.

In some cases no substitution of the current timestamp is needed. For instance, the files `bad-missing-field*.json` are used only to verify that exceptions are raised when loading malformed JSON files.

The file `ok1-fixed-timestamps.json` with fixed timestamps is required for some tests verifying data processing functionality.
