from pathlib import Path
import json
import os
import re
import tempfile
import joblib


def json_default(value):
    if hasattr(value,'isoformat'): return value.isoformat()
    if hasattr(value,'model_dump'): return value.model_dump(mode='json')
    raise TypeError(type(value).__name__)


class ArtifactRepository:
    def __init__(self,root:Path): self.root=root

    def path(self,model_id):
        if not re.fullmatch('[a-f0-9]{24}',model_id): raise KeyError('Unknown model ID.')
        return self.root/model_id

    def save(self,model_id,metadata,bundles,dataset,backtest):
        self.root.mkdir(parents=True,exist_ok=True)
        destination=self.path(model_id)
        if (destination/'metadata.json').exists(): return self.get(model_id)
        destination.mkdir(exist_ok=True)
        for name,value in [('dataset.json',dataset),('backtest.json',backtest)]:
            (destination/name).write_text(json.dumps(value,default=json_default,allow_nan=False),encoding='utf-8')
        joblib.dump(bundles,destination/'models.joblib',compress=3)
        fd,temp=tempfile.mkstemp(dir=destination,suffix='.tmp')
        with os.fdopen(fd,'w',encoding='utf-8') as file:
            json.dump(metadata,file,default=json_default,allow_nan=False)
        os.replace(temp,destination/'metadata.json')
        return self.get(model_id)

    def get(self,model_id):
        path=self.path(model_id)/'metadata.json'
        if not path.exists(): raise KeyError('Model not found. Train an eligible target first.')
        return json.loads(path.read_text(encoding='utf-8'))

    def list(self):
        if not self.root.exists(): return []
        return [self.get(p.parent.name) for p in sorted(self.root.glob('*/metadata.json')) if re.fullmatch('[a-f0-9]{24}',p.parent.name)]

    def backtest(self,model_id):
        self.get(model_id)
        return json.loads((self.path(model_id)/'backtest.json').read_text(encoding='utf-8'))
