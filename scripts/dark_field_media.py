"""Emit native-render instructions or encode completed 4K proof frames."""
import argparse
import json
from pathlib import Path
import subprocess
import imageio_ffmpeg
from PIL import Image
from video_contracts import read,write

RENDER=r'''(function(){var out=OUTPUT;function save(n,s){var f=new File(out+'/'+n);f.open('w');f.write(s);f.close();}
try{if(app.project.renderQueue.rendering)throw Error('Busy');if(!app.project.file||app.project.file.fsName!==new File(out+'/DARK_FIELD.aep').fsName)throw Error('Wrong project');
var frames=new Folder(out+'/frames');if(frames.exists)throw Error('Preserve prior output');frames.create();
var f=new File(out+'/COMP_ID.txt');f.open('r');var c=app.project.itemByID(Number(f.read()));f.close();if(c.width!==3840||c.duration!==20)throw Error('Wrong comp');
for(var i=1;i<=app.project.renderQueue.numItems;i++)if(app.project.renderQueue.item(i).status===RQItemStatus.QUEUED)app.project.renderQueue.item(i).render=false;
app.setMultiFrameRenderingConfig(false,100);app.purge(PurgeTarget.ALL_CACHES);
var q=app.project.renderQueue.items.add(c);q.applyTemplate('最佳设置');q.setSetting('Resolution','Full');var om=q.outputModule(1),preset=null;
for(i=0;i<om.templates.length;i++)if(om.templates[i].indexOf('TIFF')!==-1){preset=om.templates[i];break;}if(!preset)throw Error('No TIFF preset');om.applyTemplate(preset);om.file=new File(out+'/frames/frame_[####].tif');
save('RENDER_STARTED.txt','4K full resolution');app.project.renderQueue.render();if(q.status!==RQItemStatus.DONE)throw Error('Incomplete');save('RENDER_DONE.txt','480 native 4K frames');app.project.save();
}catch(e){save('RENDER_ERROR.txt',e.toString());}})();'''


def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('revision',type=Path);cli.add_argument('--encode',action='store_true');args=cli.parse_args()
    out=args.revision.resolve();plan=read(out/'PLAN.json')
    if not args.encode:
        (out/'render.jsx').write_text(RENDER.replace('OUTPUT',json.dumps(out.as_posix(),ensure_ascii=True)),encoding='utf-8');return
    if not (out/'RENDER_DONE.txt').exists():raise ValueError('Native render not finished')
    frames=sorted((out/'frames').glob('*.tif'))
    if [p.name for p in frames]!=[f'frame_{i:04d}.tif' for i in range(480)]:raise ValueError('Frame sequence incomplete')
    for p in frames:
        with Image.open(p) as im:
            if im.size!=(3840,2160):raise ValueError('Native resolution changed')
    exe=imageio_ffmpeg.get_ffmpeg_exe()
    for name,duration in [('COMBINED_20S_4K',20),('LIGHT_TEST_10S_4K',10),('LIFT_TEST_5S_4K',5)]:
        dest=out/(name+'.mp4')
        if dest.exists():raise FileExistsError(dest)
        with (out/(name+'.encode.log')).open('w') as log:
            subprocess.run([exe,'-hide_banner','-nostdin','-n','-framerate','24','-i',str(out/'frames/frame_%04d.tif'),'-frames:v',str(duration*24),'-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],stdout=log,stderr=subprocess.STDOUT,check=True)
    write(out/'MEDIA_RECEIPT.json',dict(native_frames=480,resolution=[3840,2160],fps=24,mode=plan['proof']['mode'],audio=False,public_render_ready=False))
    print('Encoded native 4K 20s / 10s / 5s proofs')


if __name__=='__main__':main()
