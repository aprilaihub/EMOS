%%Author: Chien-Ting Tung, PhD at University of California, Berkeley
%%reference: http://yrwu-wk.ee.ntu.edu.tw/index.php/teaching-course/

function [Ec,Efn,Efp] = solve(q,kbT,Nx,Ny,dx,dy,NB,EP,Eg,un,up,vsat_n,vsat_p,pow_n,pow_p,Nc,Nv,xi,tch1,tch2,lch1,lch2,Ec1,Ec2,Ec3,Ec4,Ef1,Ef2,Ef3,Ef4)
    error=1;
    %initial guess
    EcR=sparse(Nx*Ny,1);
    Ec=zeros(Nx,Ny);
    Efn=zeros(Nx,Ny);
    Efp=zeros(Nx,Ny);
    [A,bd]=getA2d(Nx,Ny,dx,dy,EP,xi,tch1,tch2,lch1,lch2,Ec1,Ec2,Ec3,Ec4);
    
    while error>1e-6
        [Ec,error]=poisson2d(q,kbT,Nx,Ny,A,bd,Ec,Efn,Efp,Eg,Nc,Nv,NB);
        [Efn,Efp] = driftdiff2d(kbT,Nx,Ny,dx,dy,Ec,Efn,Efp,Eg,un,up,vsat_n,vsat_p,pow_n,pow_p,Nc,Nv,Ef1,Ef2,Ef3,Ef4,tch1,tch2,lch1,lch2);
    end
end

