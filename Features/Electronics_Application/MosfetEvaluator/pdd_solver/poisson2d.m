%%Author: Chien-Ting Tung, PhD at University of California, Berkeley
%%reference: http://yrwu-wk.ee.ntu.edu.tw/index.php/teaching-course/

function [Ec,error]=poisson2d(q,kbT,Nx,Ny,A,bd,Ec,Efn,Efp,Eg,Nc,Nv,NB)
    LHS=A;
    RHS=bd;
    EcR=reshape(Ec.',[Ny*Nx,1]);
    Ev=Ec-Eg;
    n=Nc.*exp((Efn-Ec)/kbT); %Boltzmann
    p=Nv.*exp((Ev-Efp)/kbT); %Boltzmann
    for i=1:Nx
        for j=1:Ny
            m=findij(i,j,Nx,Ny);
            if m>0
                RHS(m,1)=RHS(m,1)-q*q*(n(i,j)-p(i,j)-NB(i,j));
                LHS(m,m)=LHS(m,m)-q*q/kbT*(n(i,j)+p(i,j)); %Boltzmann
            end
        end
    end
    RHS=RHS-A*EcR;
    delta=real(LHS\RHS);
    EcR=EcR+delta;
    error=max(abs(delta))/q;
    Ec=reshape(EcR,[Ny,Nx]).';
end

