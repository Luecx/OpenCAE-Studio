const KIND={t3:0,t6:1,q4:2,q8:3};
const EDGE_DEFS={
1:[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]],
2:[[0,1],[1,2],[2,0],[3,4],[4,5],[5,3],[0,3],[1,4],[2,5]],
3:[[0,1],[1,2],[2,0],[0,3],[1,3],[2,3]],
4:[[0,8,1],[1,9,2],[2,10,3],[3,11,0],[4,12,5],[5,13,6],[6,14,7],[7,15,4],[0,16,4],[1,17,5],[2,18,6],[3,19,7]],
5:[[0,6,1],[1,7,2],[2,8,0],[3,9,4],[4,10,5],[5,11,3],[0,12,3],[1,13,4],[2,14,5]],
6:[[0,4,1],[1,5,2],[2,6,0],[0,7,3],[1,8,3],[2,9,3]],
7:[[0,1],[1,2],[2,0]],8:[[0,3,1],[1,4,2],[2,5,0]],9:[[0,1],[1,2],[2,3],[3,0]],10:[[0,4,1],[1,5,2],[2,6,3],[3,7,0]],11:[[0,1]],12:[[0,2,1]],
};

const SURFACE_VS=`#version 300 es
precision highp float;precision highp int;precision highp usampler2D;
layout(location=0)in vec2 aUV;
uniform usampler2D uConn0,uConn1;uniform sampler2D uPosTex,uField0,uField1,uDispTex;uniform int uNodeTexWidth,uFaceTexWidth,uKind,uComponent,uComponentCount,uScalarMode;uniform ivec4 uStress0;uniform ivec2 uStress1;uniform bool uHighOrder,uDeformed;uniform float uDeformScale,uAnimFactor;uniform mat4 uVP;
out float vScalar;out vec3 vWorld;flat out uint vElement;
uniform usampler2D uElementTex;
ivec2 tc(int i,int w){return ivec2(i%w,i/w);}vec4 nf(sampler2D t,uint i){return texelFetch(t,tc(int(i),uNodeTexWidth),0);}uint compU(uvec4 a,int i){return i==0?a.x:i==1?a.y:i==2?a.z:a.w;}
float comp(vec4 a,vec4 b,int i){if(i<0)return 0.;if(i<4)return i==0?a.x:i==1?a.y:i==2?a.z:a.w;int j=i-4;return j==0?b.x:j==1?b.y:j==2?b.z:b.w;}
void basis(out float w[8]){for(int i=0;i<8;i++)w[i]=0.;float a=aUV.x,b=aUV.y;if(uKind==0||uKind==1){float c=1.-a-b;if(uKind==1&&uHighOrder){w[0]=c*(2.*c-1.);w[1]=a*(2.*a-1.);w[2]=b*(2.*b-1.);w[3]=4.*a*c;w[4]=4.*a*b;w[5]=4.*b*c;}else{w[0]=c;w[1]=a;w[2]=b;}}else{float u=a,v=b;if(uKind==3&&uHighOrder){w[0]=-.25*(1.-u)*(1.-v)*(1.+u+v);w[1]=-.25*(1.+u)*(1.-v)*(1.-u+v);w[2]=-.25*(1.+u)*(1.+v)*(1.-u-v);w[3]=-.25*(1.-u)*(1.+v)*(1.+u-v);w[4]=.5*(1.-u*u)*(1.-v);w[5]=.5*(1.+u)*(1.-v*v);w[6]=.5*(1.-u*u)*(1.+v);w[7]=.5*(1.-u)*(1.-v*v);}else{w[0]=(1.-u)*(1.-v)*.25;w[1]=(1.+u)*(1.-v)*.25;w[2]=(1.+u)*(1.+v)*.25;w[3]=(1.-u)*(1.+v)*.25;}}}
float scalarFrom(vec4 a,vec4 b){if(uScalarMode==0)return comp(a,b,uComponent);if(uScalarMode==1){float s=0.;for(int i=0;i<8;i++)if(i<uComponentCount){float x=comp(a,b,i);s+=x*x;}return sqrt(max(s,0.));}if(uScalarMode==2){float sxx=comp(a,b,uStress0.x),syy=comp(a,b,uStress0.y),szz=comp(a,b,uStress0.z),sxy=comp(a,b,uStress0.w),syz=comp(a,b,uStress1.x),szx=comp(a,b,uStress1.y);return sqrt(max(.5*((sxx-syy)*(sxx-syy)+(syy-szz)*(syy-szz)+(szz-sxx)*(szz-sxx))+3.*(sxy*sxy+syz*syz+szx*szx),0.));}return 0.;}
void main(){ivec2 fc=tc(gl_InstanceID,uFaceTexWidth);uvec4 c0=texelFetch(uConn0,fc,0),c1=texelFetch(uConn1,fc,0);float w[8];basis(w);vec3 p=vec3(0.);vec4 f0=vec4(0.),f1=vec4(0.);for(int i=0;i<8;i++){if(w[i]==0.)continue;uint ni=i<4?compU(c0,i):compU(c1,i-4);if(ni==0xffffffffu)continue;vec3 np=nf(uPosTex,ni).xyz;if(uDeformed)np+=uDeformScale*uAnimFactor*nf(uDispTex,ni).xyz;p+=w[i]*np;f0+=w[i]*nf(uField0,ni);f1+=w[i]*nf(uField1,ni);}vWorld=p;vScalar=scalarFrom(f0,f1)*uAnimFactor;vElement=texelFetch(uElementTex,fc,0).r;gl_Position=uVP*vec4(p,1.);}`;
const SURFACE_FS=`#version 300 es
precision highp float;precision highp int;in float vScalar;in vec3 vWorld;flat in uint vElement;out vec4 o;
uniform float uMin,uMax;uniform int uPalette,uLevels;uniform bool uContinuous,uOutside,uClipEnabled,uHasField;uniform vec3 uBelow,uAbove,uClipOrigin,uClipNormal;uniform float uClipSign;
vec3 vir(float t){vec3 a=vec3(.267,.005,.329),b=vec3(.230,.322,.546),c=vec3(.128,.567,.551),d=vec3(.369,.789,.383),e=vec3(.993,.906,.144);float x=t*4.;return x<1.?mix(a,b,x):x<2.?mix(b,c,x-1.):x<3.?mix(c,d,x-2.):mix(d,e,x-3.);}
vec3 divg(float t){vec3 a=vec3(.193,.211,.576),b=vec3(.271,.557,.753),c=vec3(.94,.95,.9),d=vec3(.992,.682,.38),e=vec3(.647,0.,.149);float x=t*4.;return x<1.?mix(a,b,x):x<2.?mix(b,c,x-1.):x<3.?mix(c,d,x-2.):mix(d,e,x-3.);}
vec3 turbo(float x){x=clamp(x,0.,1.);vec4 kRed=vec4(.13572138,4.61539260,-42.66032258,132.13108234);vec4 kGreen=vec4(.09140261,2.19418839,4.84296658,-14.18503333);vec4 kBlue=vec4(.10667330,12.64194608,-60.58204836,110.36276771);vec2 kRed2=vec2(-152.94239396,59.28637943),kGreen2=vec2(4.27729857,2.82956604),kBlue2=vec2(-89.90310912,27.34824973);vec4 v4=vec4(1.,x,x*x,x*x*x);vec2 v2=v4.zw*v4.z;return vec3(dot(v4,kRed)+dot(v2,kRed2),dot(v4,kGreen)+dot(v2,kGreen2),dot(v4,kBlue)+dot(v2,kBlue2));}
vec3 cmap(float t){if(uPalette==1)return turbo(t);if(uPalette==2)return vir(t);if(uPalette==3)return vec3(t);return divg(t);}
void main(){if(uClipEnabled&&uClipSign*dot(vWorld-uClipOrigin,uClipNormal)<0.)discard;vec3 N=normalize(cross(dFdx(vWorld),dFdy(vWorld)));if(!gl_FrontFacing)N=-N;vec3 L=normalize(vec3(.35,.55,.76));float light=.28+.72*abs(dot(N,L));if(!uHasField){o=vec4(vec3(.62,.65,.68)*light,1.);return;}if(isnan(vScalar)||isinf(vScalar))discard;if(uOutside&&vScalar<uMin){o=vec4(uBelow,1.);return;}if(uOutside&&vScalar>uMax){o=vec4(uAbove,1.);return;}float t=clamp((vScalar-uMin)/max(uMax-uMin,1e-30),0.,1.);if(!uContinuous&&uLevels>1)t=(floor(min(t,.999999)*float(uLevels))+.5)/float(uLevels);o=vec4(cmap(t)*light,1.);}`;
const PICK_FS=`#version 300 es
precision highp float;precision highp int;flat in uint vElement;in vec3 vWorld;out vec4 o;uniform bool uClipEnabled;uniform vec3 uClipOrigin,uClipNormal;uniform float uClipSign;void main(){if(uClipEnabled&&uClipSign*dot(vWorld-uClipOrigin,uClipNormal)<0.)discard;uint id=vElement+1u;o=vec4(float(id&255u),float((id>>8u)&255u),float((id>>16u)&255u),255.)/255.;}`;
const LINE_VS=`#version 300 es
precision highp float;precision highp int;layout(location=0)in uint aNode;uniform sampler2D uPosTex,uDispTex,uField0,uField1;uniform int uNodeTexWidth,uComponent,uComponentCount,uScalarMode;uniform ivec4 uStress0;uniform ivec2 uStress1;uniform bool uDeformed;uniform float uDeformScale,uAnimFactor;uniform mat4 uVP;out float vScalar;out vec3 vWorld;ivec2 tc(int i,int w){return ivec2(i%w,i/w);}vec4 nf(sampler2D t,uint i){return texelFetch(t,tc(int(i),uNodeTexWidth),0);}float comp(vec4 a,vec4 b,int i){if(i<4)return i==0?a.x:i==1?a.y:i==2?a.z:a.w;int j=i-4;return j==0?b.x:j==1?b.y:j==2?b.z:b.w;}float scalarFrom(vec4 a,vec4 b){if(uScalarMode==0)return comp(a,b,uComponent);if(uScalarMode==1){float s=0.;for(int i=0;i<8;i++)if(i<uComponentCount){float x=comp(a,b,i);s+=x*x;}return sqrt(max(s,0.));}float sxx=comp(a,b,uStress0.x),syy=comp(a,b,uStress0.y),szz=comp(a,b,uStress0.z),sxy=comp(a,b,uStress0.w),syz=comp(a,b,uStress1.x),szx=comp(a,b,uStress1.y);return sqrt(max(.5*((sxx-syy)*(sxx-syy)+(syy-szz)*(syy-szz)+(szz-sxx)*(szz-sxx))+3.*(sxy*sxy+syz*syz+szx*szx),0.));}void main(){vec3 p=nf(uPosTex,aNode).xyz;if(uDeformed)p+=uDeformScale*uAnimFactor*nf(uDispTex,aNode).xyz;vWorld=p;vec4 a=nf(uField0,aNode),b=nf(uField1,aNode);vScalar=scalarFrom(a,b)*uAnimFactor;gl_Position=uVP*vec4(p,1.);}`;
const LINE_FS=`#version 300 es
precision highp float;in float vScalar;in vec3 vWorld;out vec4 o;uniform bool uUseScalar,uClipEnabled;uniform vec4 uColor;uniform float uMin,uMax,uClipSign;uniform vec3 uClipOrigin,uClipNormal;uniform int uPalette,uLevels;uniform bool uContinuous,uOutside;uniform vec3 uBelow,uAbove;
vec3 vir(float t){vec3 a=vec3(.267,.005,.329),b=vec3(.230,.322,.546),c=vec3(.128,.567,.551),d=vec3(.369,.789,.383),e=vec3(.993,.906,.144);float x=t*4.;return x<1.?mix(a,b,x):x<2.?mix(b,c,x-1.):x<3.?mix(c,d,x-2.):mix(d,e,x-3.);}
vec3 divg(float t){vec3 a=vec3(.193,.211,.576),b=vec3(.271,.557,.753),c=vec3(.94,.95,.9),d=vec3(.992,.682,.38),e=vec3(.647,0.,.149);float x=t*4.;return x<1.?mix(a,b,x):x<2.?mix(b,c,x-1.):x<3.?mix(c,d,x-2.):mix(d,e,x-3.);}
vec3 turbo(float x){x=clamp(x,0.,1.);return clamp(vec3(1.5-abs(4.*x-3.),1.5-abs(4.*x-2.),1.5-abs(4.*x-1.)),0.,1.);}vec3 cmap(float t){if(uPalette==1)return turbo(t);if(uPalette==2)return vir(t);if(uPalette==3)return vec3(t);return divg(t);}void main(){if(uClipEnabled&&uClipSign*dot(vWorld-uClipOrigin,uClipNormal)<0.)discard;if(!uUseScalar){o=uColor;return;}if(isnan(vScalar)||isinf(vScalar))discard;if(uOutside&&vScalar<uMin){o=vec4(uBelow,1.);return;}if(uOutside&&vScalar>uMax){o=vec4(uAbove,1.);return;}float t=clamp((vScalar-uMin)/max(uMax-uMin,1e-30),0.,1.);if(!uContinuous&&uLevels>1)t=(floor(min(t,.999999)*float(uLevels))+.5)/float(uLevels);o=vec4(cmap(t),1.);}`;
const NODE_PICK_VS=`#version 300 es
precision highp float;precision highp int;uniform sampler2D uPosTex,uDispTex;uniform int uNodeTexWidth;uniform bool uDeformed;uniform float uDeformScale,uAnimFactor;uniform mat4 uVP;out vec3 vWorld;flat out uint vId;ivec2 tc(int i,int w){return ivec2(i%w,i/w);}vec4 nf(sampler2D t,uint i){return texelFetch(t,tc(int(i),uNodeTexWidth),0);}void main(){uint i=uint(gl_VertexID);vec3 p=nf(uPosTex,i).xyz;if(uDeformed)p+=uDeformScale*uAnimFactor*nf(uDispTex,i).xyz;vWorld=p;vId=i;gl_Position=uVP*vec4(p,1.);gl_PointSize=13.;}`;
const NODE_PICK_FS=`#version 300 es
precision highp float;precision highp int;in vec3 vWorld;flat in uint vId;out vec4 o;uniform bool uClipEnabled;uniform vec3 uClipOrigin,uClipNormal;uniform float uClipSign;void main(){vec2 p=gl_PointCoord*2.-1.;if(dot(p,p)>1.)discard;if(uClipEnabled&&uClipSign*dot(vWorld-uClipOrigin,uClipNormal)<0.)discard;uint id=vId+1u;o=vec4(float(id&255u),float((id>>8u)&255u),float((id>>16u)&255u),255.)/255.;}`;
const HILITE_VS=`#version 300 es
precision highp float;precision highp int;layout(location=0)in uint aNode;uniform sampler2D uPosTex,uDispTex;uniform int uNodeTexWidth;uniform bool uDeformed;uniform float uDeformScale,uAnimFactor;uniform mat4 uVP;ivec2 tc(int i,int w){return ivec2(i%w,i/w);}vec3 pos(uint i){vec3 p=texelFetch(uPosTex,tc(int(i),uNodeTexWidth),0).xyz;if(uDeformed)p+=uDeformScale*uAnimFactor*texelFetch(uDispTex,tc(int(i),uNodeTexWidth),0).xyz;return p;}void main(){gl_Position=uVP*vec4(pos(aNode),1.);gl_PointSize=11.;}`;
const HILITE_FS=`#version 300 es
precision highp float;out vec4 o;uniform vec4 uColor;uniform bool uPoint;void main(){if(uPoint){vec2 p=gl_PointCoord*2.-1.;if(dot(p,p)>1.)discard;}o=uColor;}`;
const PLANE_VS=`#version 300 es
precision highp float;layout(location=0)in vec3 aPos;uniform mat4 uVP;void main(){gl_Position=uVP*vec4(aPos,1.);}`;
const PLANE_FS=`#version 300 es
precision highp float;out vec4 o;void main(){o=vec4(.68,.76,.84,.12);}`;

export {KIND,EDGE_DEFS,SURFACE_VS,SURFACE_FS,PICK_FS,LINE_VS,LINE_FS,NODE_PICK_VS,NODE_PICK_FS,HILITE_VS,HILITE_FS,PLANE_VS,PLANE_FS};
