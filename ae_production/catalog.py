"""Use the existing V7 dependency index for registered preview descendants."""
from copy import deepcopy
from pathlib import Path
from content_os.lifecycle import refresh_catalog
from video_contracts import read,sha,write


def register_preview(index_path,package,contract,preview,statuses):
    path=Path(index_path)
    index=read(path) if path.exists() else {'entries':[]}
    parent='frozen-package:'+sha(package)
    if not any(e['id']==parent for e in index['entries']):
        index['entries'].append({'id':parent,'kind':'package','parent_ids':[],'artifact':deepcopy(package)})
    if not any(e['id']==contract['render_id'] for e in index['entries']):
        index['entries'].append({'id':contract['render_id'],'kind':'render','parent_ids':[parent],
            'artifact':{'package_id':contract['package_id'],'package_sha':contract['package_sha'],
                        'template_version':contract['template_version'],'render_id':contract['render_id'],
                        'preview':str(Path(preview).resolve()),'source_items':[],'status':'internal_preview',
                        'invalidation':deepcopy(package['invalidation']),'render_ready_for_publication':False}})
    updated=refresh_catalog(index,statuses);write(path,updated)
    return updated


def refresh_preview_index(index_path,statuses):
    updated=refresh_catalog(read(index_path),statuses);write(index_path,updated)
    return updated
