import pathlib
import re
import json
from datetime import datetime
import scipy.io as spio
import numpy as np

"""
This module houses all loader classes for loading sessions' behavioral data
Any loader class must have the following interfaces:

    `load_sessions` function:
        Input: 
            + root_data_dir: root directory of the data for all subjects
            + subject_name: subject name (i.e. "subject_id" in lab.Subject
        Output: A list of dictionary, each represents one session to be ingested, with the following keys:
            + subject_id: (str) subject id
            + session_date: (date) session's date 
            + session_time: (time) session's time 
            + username: experimenter's username associated with this session (i.e. "username" in lab.Person)
            + rig: the rig the session performed on (i.e. "rig" in lab.Rig)
            + session_files: list of associated files (relative path with respect to the root data directory)

    `load_behavior` function:
        Input:
        Output:
            
"""


class VincentLoader:

    tracking_camera = 'WT_Camera_Vincent 0'
    tracking_fps = 500

    def __init__(self, root_data_dir, config={}):
        self.config = config
        self.root_data_dir = pathlib.Path(root_data_dir)
        self.loader_name = self.__class__.__name__

    def load_sessions(self, subject_name):
        subj_dir = self.root_data_dir / subject_name
        if not subj_dir.exists():
            raise FileNotFoundError(f'{subj_dir} not found!')

        # find all 'Analysis' folders, which contain the processed files for each session
        all_sessions = list(subj_dir.rglob('**/*info.json'))

        # ---- parse processed data folders:
        for sess in all_sessions:
            with open(sess.absolute()) as f:
                sessinfo = json.load(f)
            sess_datetime = datetime.strptime(sessinfo['date'], '%d-%b-%Y %H:%M:%S')
            # find the basename of the other related files for this session
            data_dir = sess.parent
            # find all associated files
            session_files = [sess.relative_to(self.root_data_dir)
                             for sess in data_dir.glob(f'{data_dir.name}*')]

            yield {'subject_id': subject_name,
                   'session_date': sess_datetime.date(),
                   'session_time': sess_datetime.time(),
                   'session_files': session_files,
                   'username': self.config['custom']['username'],
                   'rig': self.config['custom']['rig']}

    def load_behavior(self):
        pass

    def load_tracking(self, session_dir, subject_name, session_datetime):

        # ---- identify the .mat file for tracking data ----
        tracking_dir = session_dir / 'WhiskerTracking'
        if not tracking_dir.exists():
            raise FileNotFoundError(f'{tracking_dir} not found!')
        datetime_str = datetime.strftime(session_datetime, '%Y%m%d%H%M%S')

        tracking_fp = list(tracking_dir.glob(f'{subject_name}*{datetime_str}*.mat'))

        if len(tracking_fp) != 1:
            raise FileNotFoundError(f'Unable to find tracking .mat - Found: {tracking_fp}')
        else:
            tracking_fp = tracking_fp[0]

        # ---- load .mat and extract whisker data ----
        trk_mat = spio.loadmat(tracking_fp, struct_as_record=False, squeeze_me=True)[tracking_fp.stem]

        frames = np.arange(max(trk_mat.fid) + 1)

        whisker_inds = np.unique(trk_mat.wid)
        whiskers = {wid: {} for wid in whisker_inds}
        for wid in whisker_inds:
            matched_wid = trk_mat.wid == wid
            matched_fid = trk_mat.fid[matched_wid]
            _, matched_frame_idx, _ = np.intersect1d(matched_fid, frames, return_indices=True)

            for var in ('follicle_x', 'follicle_y', 'angle'):
                d = np.full(len(frames), np.nan)
                d[matched_frame_idx] = getattr(trk_mat, var)[matched_wid]
                whiskers[wid][var] = d

        # ---- return ----
        return {'tracking_device': self.tracking_camera,
                'tracking_timestamps': frames * self.fps,
                'tracking_files': [tracking_fp.relative_to(self.root_data_dir)],
                'WhiskerTracking': [{'whisker_idx': wid, **wdata} for wid, wdata in whiskers.items()]}

    def load_ephys(self):
        pass
