"""Resume a native 1080p question render in short cache-purged batches."""
import argparse
import json
from pathlib import Path
from PIL import Image
from video_contracts import read, write


TEMPLATE=r'''(function(){var out=OUTPUT,start=START;function save(n,s){var f=new File(out+'/'+n);f.open('w');f.write(s);f.close();}
try{if(app.project.renderQueue.rendering)throw Error('Already rendering');if(!app.project.file||app.project.file.fsName!==new File(out+'/CONTINUOUS_QUESTION.aep').fsName)throw Error('Wrong project');
var file=new File(out+'/RENDER_COMP_ID.txt');file.open('r');var comp=app.project.itemByID(Number(file.read()));file.close();
if(comp.name!=='QUESTION_NATIVE_4K'||comp.duration!==70||comp.frameRate!==24)throw Error('Wrong review comp');
app.setMultiFrameRenderingConfig(false,100);
for(var at=start;at<1680;at+=48){app.purge(PurgeTarget.ALL_CACHES);var count=Math.min(48,1680-at),folder=new Folder(out+'/chunk-'+at);if(folder.exists)throw Error('Preserve earlier chunk');folder.create();
for(var i=1;i<=app.project.renderQueue.numItems;i++)if(app.project.renderQueue.item(i).status===RQItemStatus.QUEUED)app.project.renderQueue.item(i).render=false;
var q=app.project.renderQueue.items.add(comp);q.applyTemplate('最佳设置');q.setSetting('Resolution','Half');q.timeSpanStart=at/24;q.timeSpanDuration=count/24;
var om=q.outputModule(1),preset=null;for(i=0;i<om.templates.length;i++)if(om.templates[i].indexOf('TIFF')!==-1){preset=om.templates[i];break;}if(!preset)throw Error('No TIFF preset');om.applyTemplate(preset);om.file=new File(folder.fsName+'/frame_[####].tif');
save('CHUNK_PROGRESS.txt',at+' / 1680');app.project.renderQueue.render();if(q.status!==RQItemStatus.DONE)throw Error('Chunk incomplete at '+at);}
app.purge(PurgeTarget.ALL_CACHES);app.project.save();save('CHUNKS_DONE.txt','Native batches complete');
}catch(e){save('CHUNKS_ERROR.txt',e.toString());}})();'''


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('revision',type=Path);cli.add_argument('--collect',action='store_true')
    a=cli.parse_args();out=a.revision.resolve();folder=out/'native-frames'
    if not a.collect:
        files=sorted(folder.glob('frame_*.tif'))
        if [f.name for f in files]!=[f'frame_{i:04d}.tif' for i in range(len(files))]:
            raise ValueError('Existing native frames must be contiguous')
        for f in files:
            with Image.open(f) as im:
                if im.size!=(1920,1080):raise ValueError('Unexpected resolution')
                im.load()
        if len(files)>=1680:raise ValueError('No remaining frames')
        manifest=out/'CHUNK_PLAN.json'
        if manifest.exists():raise FileExistsError('Preserve earlier chunk attempt')
        write(manifest,dict(start=len(files),end=1680,batch=48,existing_frames_verified=True))
        source=TEMPLATE.replace('OUTPUT',json.dumps(out.as_posix())).replace('START',str(len(files)))
        (out/'render-chunks.jsx').write_text(source,encoding='utf-8')
        print('Resume at frame',len(files));return
    if not (out/'CHUNKS_DONE.txt').exists():raise ValueError('Native batches incomplete')
    plan=read(out/'CHUNK_PLAN.json');moved=0
    for start in range(plan['start'],1680,48):
        batch=out/f'chunk-{start}';files=sorted(batch.glob('frame_*.tif'));count=min(48,1680-start)
        numbers=[int(f.stem.split('_')[-1]) for f in files]
        if numbers not in (list(range(count)),list(range(start,start+count))):raise ValueError('Unexpected chunk numbering')
        for offset,source in enumerate(files):
            target=folder/f'frame_{start+offset:04d}.tif'
            if not source.resolve().is_relative_to(out) or not target.resolve().is_relative_to(out):raise ValueError('Path escaped review directory')
            if target.exists():raise FileExistsError(target)
            with Image.open(source) as im:
                if im.size!=(1920,1080):raise ValueError('Wrong review dimensions')
                im.load()
            source.rename(target);moved+=1
    write(out/'CHUNK_RECEIPT.json',dict(preserved_frames=plan['start'],new_frames=moved,cache_purged_between_batches=True))
    (out/'FRAMES_DONE.txt').write_text('1680 native 1080p frames; contiguous resumed batches',encoding='utf-8')
    print('Native sequence complete')


if __name__=='__main__':main()
