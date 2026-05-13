%%Author: Chien-Ting Tung, PhD at University of California, Berkeley
%%reference: http://yrwu-wk.ee.ntu.edu.tw/index.php/teaching-course/

clear all
close all
constant
T=300;
kbT=kb*T;

%short channel
dx=5e-10; 
dy=5e-10;
L=14e-9; %channel length
sd=4e-9; %source/drain length
Tox=1e-9; %oxide thickness
Tch=4e-9; %channel thickness
%boundary considiotn
phig=3.65;
phisd=0.0;
 
% %long channel
% dx=20e-9; 
% dy=5e-10;
% L=1e-6; %channel length
% sd=40e-9; %source/drain length
% Tox=1e-9; %oxide thickness
% Tch=5e-9; %channel thickness
% %boundary considiotn
% phig=3.5;
% phisd=0.0;

Ns=ceil(sd/dx);
Nc=ceil(L/dx);
Nd=ceil(sd/dx);
Nx=Ns+Nc+Nd;
lch1=Ns+1; %begin of channel
lch2=Ns+Nc; %end of channel

No=ceil(Tox/dy);
Nt=ceil(Tch/dy);
Ny=No*2+Nt;
tch1=No+1; %top of channel
tch2=No+Nt; %bottom of channel

x=dx*linspace(0,Nx,Nx).';
y=dy*linspace(0,Ny,Ny).';

% define structure
%      Ec3
%      tox
%Ec1----------Ec2
%      tox
%      Ec4
%    y  |
%    x  ->

Nc=ones(Nx,Ny)*Ins_Nc;
Nc(:,tch1:tch2)=Si_Nc;

Nv=ones(Nx,Ny)*Ins_Nv;
Nv(:,tch1:tch2)=Si_Nv;

un=ones(Nx,Ny)*Ins_un;
un(:,tch1:tch2)=Si_un;

up=ones(Nx,Ny)*Ins_up;
up(:,tch1:tch2)=Si_up;

vsat_n=ones(Nx,Ny)*Ins_vsat_n;
vsat_n(:,tch1:tch2)=Si_vsat_n;

vsat_p=ones(Nx,Ny)*Ins_vsat_p;
vsat_p(:,tch1:tch2)=Si_vsat_p;

pow_n=ones(Nx,Ny)*Ins_pow_n;
pow_n(:,tch1:tch2)=Si_pow_n;

pow_p=ones(Nx,Ny)*Ins_pow_p;
pow_p(:,tch1:tch2)=Si_pow_p;

Eg=ones(Nx,Ny)*q*Ins_Eg;
Eg(:,tch1:tch2)=q*Si_Eg;

EP=ones(Nx,Ny)*ep0*Ins_ep;
EP(:,tch1:tch2)=ep0*Si_ep;

xi=ones(Nx,Ny)*q*Ins_xi;
xi(:,tch1:tch2)=q*Si_xi;

% define doping
NB=zeros(Nx,Ny);
NB(lch1:lch2,tch1:tch2)=1e6*-1e15;
NB(1:lch1-1,tch1:tch2)=1e6*1e20;
NB(lch2+1:Nx,tch1:tch2)=1e6*1e20;

%Start
Nvg=14;
Vgs=linspace(0,0.7,Nvg);
Nvd=13;
Vds=linspace(0.0,0.7,Nvd);
for i=1:Nvg
    for j=1:Nvd
         Ef1=0; Ef2=-q*Vds(j); Ef3=-q*Vgs(i); Ef4=-q*Vgs(i);
         Ec1=q*phisd+Ef1; Ec2=q*phisd+Ef2; Ec3=q*phig+Ef3; Ec4=q*phig+Ef4;
         [Ec,Efn,Efp] = solve(q,kbT,Nx,Ny,dx,dy,NB,EP,Eg,un,up,vsat_n,vsat_p,pow_n,pow_p,Nc,Nv,xi,tch1,tch2,lch1,lch2,Ec1,Ec2,Ec3,Ec4,Ef1,Ef2,Ef3,Ef4);
         Ev=Ec-Eg;
         n=Nc.*exp((Efn-Ec)/kbT); p=Nv.*exp((Ev-Efp)/kbT);
         Jn=un./(1+(abs(gradient(Ec.').')/dx.*un/q./vsat_n).^pow_n).^(1./pow_n).*n.*gradient(Efn.').'/dx;
         Jp=up./(1+(abs(gradient(Ec.').')/dx.*up/q./vsat_p).^pow_p).^(1./pow_p).*p.*gradient(Efp.').'/dx;
         %Jn=un.*n.*gradient(Efn.').'/dx;
         %Jp=up.*p.*gradient(Efp.').'/dx;
         J(i,j)=-sum(Jn(Nx,tch1:tch2)+Jp(Nx,tch1:tch2))*dy;
         Q(i,j)=-q*sum(n(lch1:lch2,tch1:tch2)-p(lch1:lch2,tch1:tch2)-NB(lch1:lch2,tch1:tch2),'all')*dx*dy;
         figure(1)
         plot(x,Ec(:,tch1)/q,x,Ev(:,tch1)/q,x,Efn(:,tch1)/q);
         title('Channel Band-diagram')
    end
end
figure(2)
plot(Vgs,J(:,2:Nvd))
title('Linear Id/W-Vg')
figure(3)
semilogy(Vgs,J(:,2:Nvd))
title('Log Id/W-Vg')
figure(4)
plot(Vds,J.')
title('Id/W-Vd')
figure(5)
plot(Vgs,-gradient(Q.')./gradient(Vgs));
title('Cgg/W-Vg')