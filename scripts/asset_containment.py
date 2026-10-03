"""Constrain externally supplied asset identifiers to one owned workspace."""
import pathlib,re

def asset_output_path(root,asset_id,suffix):
    value=str(asset_id)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',value) or value in {'.','..'}:raise ValueError('unsafe asset identifier')
    if '/' in suffix or '\\' in suffix:raise ValueError('unsafe asset suffix')
    root=pathlib.Path(root).resolve();target=root/(value+suffix)
    if target.is_symlink() or not target.resolve().is_relative_to(root):raise ValueError('asset output escapes owned workspace')
    return target
