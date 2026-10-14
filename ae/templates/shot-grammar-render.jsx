// Native lossless frames avoid this workstation's stalled direct H.264 encoder.
(function(){var out=SHOT_PREVIEW_OUTPUT;
function save(n,s){var f=new File(out+'/'+n);f.encoding='UTF-8';f.open('w');f.write(s);f.close();}
try{
 if(!app.project.file||app.project.file.fsName!==new File(out+'/CONTINUOUS_QUESTION.aep').fsName)throw Error('Wrong bound project');
 if(app.project.renderQueue.rendering)throw Error('Already rendering');
 var folder=new Folder(out+'/native-frames');if(folder.exists)throw Error('Preserve prior frame output');folder.create();
 var f=new File(out+'/RENDER_COMP_ID.txt');f.open('r');var id=Number(f.read());f.close();
 var comp=app.project.itemByID(id);if(!(comp instanceof CompItem)||comp.name!=='QUESTION_NATIVE_4K'||comp.duration!==70)throw Error('Wrong native master');
 for(var i=1;i<=app.project.renderQueue.numItems;i++)if(app.project.renderQueue.item(i).status===RQItemStatus.QUEUED)app.project.renderQueue.item(i).render=false;
 app.setMultiFrameRenderingConfig(false,100);app.purge(PurgeTarget.ALL_CACHES);
 // Single-frame rendering preserves memory headroom; no post-production time stretch.
 var q=app.project.renderQueue.items.add(comp);q.applyTemplate('最佳设置');q.setSetting('Resolution','Half');
 q.timeSpanStart=0;q.timeSpanDuration=comp.duration;
 var om=q.outputModule(1),preset=null;
 for(i=0;i<om.templates.length;i++)if(om.templates[i].indexOf('TIFF')!==-1){preset=om.templates[i];break;}
 if(!preset)throw Error('Native TIFF sequence unavailable');om.applyTemplate(preset);
 om.file=new File(folder.fsName+'/frame_[####].tif');app.project.save();save('FRAMES_STARTED.txt',String(id));
 app.project.renderQueue.render();if(q.status!==RQItemStatus.DONE)throw Error('Native frames incomplete');
 save('FRAMES_DONE.txt','1680 native frames; 1920x1080; 24fps; master 4K');app.project.save();
}catch(e){save('FRAMES_ERROR.txt',e.toString());}
})();
