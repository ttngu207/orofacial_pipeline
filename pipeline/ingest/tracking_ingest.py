import datajoint as dj
from pipeline import lab, experiment, tracking
from pipeline import get_schema_name

from pipeline.ingest import session_ingest, get_loader

schema = dj.schema(get_schema_name('ingestion'))


@schema
class TrackingIngestion(dj.Imported):
    definition = """
    -> session_ingest.InsertedSession
    """

    class TrackingFile(dj.Part):
        definition = """  # file(s) associated with a session
        -> master
        filepath: varchar(255)  # relative filepath with respect to root data directory
        """

    def make(self, key):
        loader = get_loader()
        sess_dir = (session_ingest.InsertedSession & key).fetch1('sess_data_dir')
        sess_dir = loader.root_data_dir / sess_dir
        tracking_data = loader.load_tracking(key, sess_dir)
        pass

