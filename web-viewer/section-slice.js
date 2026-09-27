const CACHE=new Map();

function hexWeights(type,ref,high=true){
  const [x,y,z]=ref,n=type===4?20:8,w=new Float64Array(n);
  const c=[[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]];
  if(type===1||!high){
    for(let i=0;i<8;i++){const [a,b,d]=c[i];w[i]=.125*(1+a*x)*(1+b*y)*(1+d*z);}return w;
  }
  for(let i=0;i<8;i++){const[a,b,d]=c[i];w[i]=.125*(1+a*x)*(1+b*y)*(1+d*z)*(a*x+b*y+d*z-2);}
  w[8]=.25*(1-x*x)*(1-y)*(1-z);w[9]=.25*(1-y*y)*(1+x)*(1-z);
  w[10]=.25*(1-x*x)*(1+y)*(1-z);w[11]=.25*(1-y*y)*(1-x)*(1-z);
  w[12]=.25*(1-z*z)*(1-x)*(1-y);w[13]=.25*(1-z*z)*(1+x)*(1-y);
  w[14]=.25*(1-z*z)*(1+x)*(1+y);w[15]=.25*(1-z*z)*(1-x)*(1+y);
  w[16]=.25*(1-x*x)*(1-y)*(1+z);w[17]=.25*(1-y*y)*(1+x)*(1+z);
  w[18]=.25*(1-x*x)*(1+y)*(1+z);w[19]=.25*(1-y*y)*(1-x)*(1+z);
  return w;
}
function tetWeights(type,ref,high=true){
  const [r,s,t]=ref,n=type===6?10:4,w=new Float64Array(n),L=[1-r-s-t,r,s,t];
  if(type===3||!high){for(let i=0;i<4;i++)w[i]=L[i];return w;}
  for(let i=0;i<4;i++)w[i]=L[i]*(2*L[i]-1);
  w[4]=4*L[0]*L[1];w[5]=4*L[1]*L[2];w[6]=4*L[2]*L[0];
  w[7]=4*L[0]*L[3];w[8]=4*L[1]*L[3];w[9]=4*L[2]*L[3];
  return w;
}
function wedgeWeights(type,ref,high=true){
  const [r,s,t]=ref,n=type===5?15:6,w=new Float64Array(n),L1=1-r-s,L2=r,L3=s;
  if(type===2||!high){const a=.5*(1-t),b=.5*(1+t);w[0]=L1*a;w[1]=L2*a;w[2]=L3*a;w[3]=L1*b;w[4]=L2*b;w[5]=L3*b;return w;}
  w[0]=.5*L1*(1-t)*(2*L1-2-t);w[1]=.5*L2*(1-t)*(2*L2-2-t);w[2]=.5*L3*(1-t)*(2*L3-2-t);
  w[3]=.5*L1*(1+t)*(2*L1-2+t);w[4]=.5*L2*(1+t)*(2*L2-2+t);w[5]=.5*L3*(1+t)*(2*L3-2+t);
  w[6]=2*L1*L2*(1-t);w[7]=2*L2*L3*(1-t);w[8]=2*L3*L1*(1-t);
  w[9]=L1*(1-t*t);w[10]=L2*(1-t*t);w[11]=L3*(1-t*t);
  w[12]=2*L1*L2*(1+t);w[13]=2*L2*L3*(1+t);w[14]=2*L3*L1*(1+t);
  return w;
}
function weights(type,ref,high){if(type===1||type===4)return hexWeights(type,ref,high);if(type===3||type===6)return tetWeights(type,ref,high);return wedgeWeights(type,ref,high);}

function hexMesh(type,high){
  const n=high&&type===4?2:1,refs=[],idx=(i,j,k)=>k*(n+1)*(n+1)+j*(n+1)+i;
  for(let k=0;k<=n;k++)for(let j=0;j<=n;j++)for(let i=0;i<=n;i++)refs.push([-1+2*i/n,-1+2*j/n,-1+2*k/n]);
  const tets=[];
  for(let k=0;k<n;k++)for(let j=0;j<n;j++)for(let i=0;i<n;i++){
    const v=[idx(i,j,k),idx(i+1,j,k),idx(i+1,j+1,k),idx(i,j+1,k),idx(i,j,k+1),idx(i+1,j,k+1),idx(i+1,j+1,k+1),idx(i,j+1,k+1)];
    tets.push([v[0],v[1],v[2],v[6]],[v[0],v[2],v[3],v[6]],[v[0],v[3],v[7],v[6]],[v[0],v[7],v[4],v[6]],[v[0],v[4],v[5],v[6]],[v[0],v[5],v[1],v[6]]);
  }
  return{refs,tets};
}
function tetMesh(type,high){
  if(type===3||!high)return{refs:[[0,0,0],[1,0,0],[0,1,0],[0,0,1]],tets:[[0,1,2,3]]};
  return{refs:[[0,0,0],[1,0,0],[0,1,0],[0,0,1],[.5,0,0],[.5,.5,0],[0,.5,0],[0,0,.5],[.5,0,.5],[0,.5,.5]],tets:[[0,4,6,7],[4,1,5,8],[6,5,2,9],[7,8,9,3],[4,5,6,9],[4,5,8,9],[4,8,7,9],[4,7,6,9]]};
}
function wedgeMesh(type,high){
  const n=high&&type===5?2:1,nz=n,refs=[],layer=[],tris=[];
  for(let k=0;k<=nz;k++){const map=new Map();for(let j=0;j<=n;j++)for(let i=0;i<=n-j;i++){map.set(i+","+j,refs.length);refs.push([i/n,j/n,-1+2*k/nz]);}layer.push(map);}
  for(let j=0;j<n;j++)for(let i=0;i<n-j;i++){tris.push([[i,j],[i+1,j],[i,j+1]]);if(i+j<n-1)tris.push([[i+1,j],[i+1,j+1],[i,j+1]]);}
  const tets=[];
  for(let k=0;k<nz;k++)for(const tri of tris){
    const a=layer[k].get(tri[0][0]+","+tri[0][1]),b=layer[k].get(tri[1][0]+","+tri[1][1]),c=layer[k].get(tri[2][0]+","+tri[2][1]),A=layer[k+1].get(tri[0][0]+","+tri[0][1]),B=layer[k+1].get(tri[1][0]+","+tri[1][1]),C=layer[k+1].get(tri[2][0]+","+tri[2][1]);
    tets.push([a,b,c,A],[b,c,B,A],[c,B,C,A]);
  }
  return{refs,tets};
}
export function sectionReferenceMesh(type,highOrder=true){
  const key=type+":"+(highOrder?1:0);if(CACHE.has(key))return CACHE.get(key);
  let m;if(type===1||type===4)m=hexMesh(type,highOrder);else if(type===3||type===6)m=tetMesh(type,highOrder);else if(type===2||type===5)m=wedgeMesh(type,highOrder);else m={refs:[],tets:[]};
  m.weights=m.refs.map(r=>weights(type,r,highOrder));CACHE.set(key,m);return m;
}
