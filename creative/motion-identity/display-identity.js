// Drawing primitives for the existing Canvas path, not a renderer or timeline.
// The caller supplies the canvas context and explicitly opts into a display role.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const filename = path.join(__dirname, 'display-identity.json');
const bytes = fs.readFileSync(filename), profile = JSON.parse(bytes);
const sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
function clamp(k) { return Math.max(0, Math.min(1, k)); }
function progress(t, start, end) { const k = clamp((t-start)/(end-start)); return k>=1 ? 1 : 1-Math.pow(2,-10*k); }
function text(ctx, value, role, options={}) {
  if (!profile.type[role] || typeof value!=='string' || !value.trim()) throw Error('Invalid display text role/content');
  const s={...profile.type[role],...options};
  const alpha=s.alpha===undefined ? 1 : s.alpha;
  if (![s.x_px,s.baseline_y_px,s.size_px,s.tracking_px,alpha].every(Number.isFinite)) throw Error('Non-finite display geometry');
  ctx.save();ctx.font=`${s.weight} ${s.size_px}px "${s.font_family||profile.type.chinese_family}"`;
  ctx.textBaseline='alphabetic';ctx.textAlign='left';
  const glyphs=Array.from(value),width=glyphs.reduce((n,c)=>n+ctx.measureText(c).width,0)+s.tracking_px*(glyphs.length-1);
  const safe=s.safe_width_px===undefined ? 1720 : s.safe_width_px;
  if (width>safe) { ctx.restore(); throw Error('Display text overflow; author layout decision required'); }
  let x=s.x_px-width/2;
  ctx.globalAlpha*=clamp(alpha);ctx.fillStyle=s.color||profile.palette.primary;
  for(const c of glyphs){ctx.fillText(c,x,s.baseline_y_px);x+=ctx.measureText(c).width+s.tracking_px;}
  ctx.restore();return {text:value,role,width_px:width,...s,profile_id:profile.profile_id,profile_sha256:sha256};
}
function background(ctx,t){
  ctx.save();ctx.fillStyle=profile.palette.background;ctx.fillRect(0,0,1920,1080);
  const g=ctx.createRadialGradient(960,540,378,960,540,1026);g.addColorStop(0,'rgba(0,0,0,0)');g.addColorStop(1,`rgba(0,0,0,${profile.surface.vignette_alpha})`);
  ctx.fillStyle=g;ctx.fillRect(0,0,1920,1080);
  const hash=n=>{const v=Math.sin(n*127.1+311.7)*43758.5453;return v-Math.floor(v);};
  const seed=Math.floor(t*24);ctx.fillStyle='#ffffff';
  for(let i=0;i<profile.surface.grain_points_per_frame;i++){
    ctx.globalAlpha=profile.surface.grain_alpha*hash(i*7+seed);
    ctx.fillRect(hash(i+seed*13.1)*1920,hash(seed*9973+i)*1080,1.5,1.5);
  }
  ctx.restore();
}
module.exports={profile,sha256,filename,text,background,progress};
