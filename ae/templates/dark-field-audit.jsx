// Read-only native state verification, independent of the authored config.
(function(){
var out=DF_OUTPUT;
if(!app.project.file||app.project.file.fsName!==new File(out+'/DARK_FIELD.aep').fsName)throw Error('Wrong project');
var f=new File(out+'/COMP_ID.txt');f.open('r');var c=app.project.itemByID(Number(f.read()));f.close();
var w=c.layer('REALITY_WORLD'),r=w.source,d=r.layer('OPTION_D');
var a=d.transform.position.valueAtTime(17,false),b=d.transform.position.valueAtTime(17+10/24,false);
var bg=c.layer('ENVIRONMENT').property('ADBE Effect Parade').property(1).property('ADBE Fill-0002');
var data={world_opacity_4_5:w.transform.opacity.valueAtTime(4.5,false),
 world_blur_4_5:w.property('ADBE Effect Parade').property(1).property(1).valueAtTime(4.5,false)/2,
 world_depth_4_5:r.layer('REALITY').transform.position.valueAtTime(4.5,false)[2]/2,
 eliminate_screen_dy:(b[1]-a[1])/2*4800/6000,
 eliminate_opacity:d.transform.opacity.valueAtTime(18,false),fields:[],foreground:[]};
for(var i=0;i<=480;i++)data.fields.push(bg.valueAtTime(i/24,false));
for(var j=1;j<=c.numLayers;j++){
 var l=c.layer(j);if(l.name.indexOf('EVIDENCE_')!==0&&l.name.indexOf('OPTION_KEYWORD_')!==0)continue;
 var color=l.property('ADBE Text Properties').property('ADBE Text Animators').property(1).property('ADBE Text Animator Properties').property('ADBE Text Fill Color'),samples=[];
 for(i=0;i<=480;i++)samples.push(color.valueAtTime(i/24,false));data.foreground.push({name:l.name,color:samples});
}
f=new File(out+'/STATE_AUDIT.json');f.encoding='UTF-8';f.open('w');f.write(JSON.stringify(data));f.close();
})();
