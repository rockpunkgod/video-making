// SHOT_PREVIEW_OUTPUT is the fresh folder created by prepare_shot_preview.py.
(function(){var out=SHOT_PREVIEW_OUTPUT;
  function save(name,value){var f=new File(out+'/'+name);f.encoding='UTF-8';f.open('w');f.write(value);f.close();}
  try{
    if(!app.project.file||app.project.file.fsName!==new File(out+'/P3_PREVIEW.aep').fsName)throw Error('Wrong active preview project');
    if(app.project.renderQueue.rendering)throw Error('Render already active');
    if(new File(out+'/P3_PREVIEW_4K.mp4').exists)throw Error('Do not overwrite previous output');
    var f=new File(out+'/RENDER_COMP_ID.txt');if(!f.open('r'))throw Error('Missing native comp identity');var id=Number(f.read());f.close();
    var comp=app.project.itemByID(id);if(!(comp instanceof CompItem)||comp.name!=='P3_PREVIEW_4K')throw Error('Native comp binding changed');
    for(var i=1;i<=app.project.renderQueue.numItems;i++)if(app.project.renderQueue.item(i).status!==RQItemStatus.DONE)app.project.renderQueue.item(i).render=false;
    var r=app.project.renderQueue.items.add(comp);r.applyTemplate('最佳设置');
    r.outputModule(1).applyTemplate('H.264 - 匹配渲染设置 - 40 Mbps');
    r.outputModule(1).file=new File(out+'/P3_PREVIEW_4K.mp4');r.render=true;
    app.project.save();save('RENDER_STARTED.txt','comp_id='+id);app.project.renderQueue.render();
    if(r.status!==RQItemStatus.DONE)throw Error('Native render did not finish');
    save('RENDER_DONE.txt','comp_id='+id+'; DONE');
  }catch(e){save('RENDER_ERROR.txt',e.toString());}
})();
