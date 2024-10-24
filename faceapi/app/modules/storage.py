import os
import pickle
from pathlib import Path

import pandas as pd


class Storage:
    root_path = None

    def __init__(self):
        cwd = os.getcwd()
        self.root_path = Path(cwd)

    def get_face_id_storage_dir_path(self):
        return Path(self.root_path).joinpath("face-id-storage")

    def get_face_id_storage_models_dir_path(self):
        return self.get_face_id_storage_dir_path().joinpath("models")
    
    def get_model_weights_dir_path(self):
        return Path(self.root_path).joinpath("weights")

    def get_global_model_file_path(self):
        path = self.get_face_id_storage_models_dir_path().joinpath('global_model.pkl')
        if not path.exists():
            new_entry = pd.DataFrame({"encodings": [], "user_id": []})
            with open(path, 'wb') as file:
                pickle.dump(new_entry, file)
        return path


storage = Storage()
