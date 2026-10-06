"""Freeze a local variable font at regular weight for reproducible libass output."""
import argparse
from pathlib import Path
from creative_os.hero import file_sha
from video_contracts import write


def freeze(source,output):
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    output=Path(output)
    if output.exists():raise ValueError('Preserve existing frozen font')
    font=TTFont(source)
    if 'fvar' not in font or 'wght' not in {a.axisTag for a in font['fvar'].axes}:
        raise ValueError('A variable weight font is required')
    font=instantiateVariableFont(font,{'wght':400},inplace=False)
    names={1:'Passage Caption',2:'Regular',4:'Passage Caption Regular',6:'PassageCaption-Regular',
           16:'Passage Caption',17:'Regular'}
    for record in font['name'].names:
        if record.nameID in names:record.string=names[record.nameID].encode(record.getEncoding())
    output.parent.mkdir(parents=True,exist_ok=True);font.save(output)
    result={'source_sha':file_sha(source),'font':str(output.resolve()),'font_sha':file_sha(output),
            'family':'Passage Caption','weight':400,'redistribution':'local_only'}
    write(output.with_suffix('.json'),result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args()
    freeze(a.source,a.output)
