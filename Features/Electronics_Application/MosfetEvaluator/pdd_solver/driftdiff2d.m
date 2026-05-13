%%Author: Chien-Ting Tung, PhD at University of California, Berkeley
%%reference: http://yrwu-wk.ee.ntu.edu.tw/index.php/teaching-course/

function [Efn,Efp] = driftdiff2d(kbT,Nx,Ny,dx,dy,Ec,Efn,Efp,Eg,un,up,vsat_n,vsat_p,pow_n,pow_p,Nc,Nv,Ef1,Ef2,Ef3,Ef4,tch1,tch2,lch1,lch2)
    %saturatuion velocity model: v=un*E/(1+(un*E/vsat)^pow)^(1/pow)
    q=1.6e-19;
    nLHS=sparse(Nx*Ny,Nx*Ny);
    nRHS=sparse(Nx*Ny,1);
    pLHS=sparse(Nx*Ny,Nx*Ny);
    pRHS=sparse(Nx*Ny,1);   
    Ev=Ec-Eg;  
    for i=1:Nx
        for j=1:Ny
            if i-1<1
                Ncmi=Nc(1,j);
                unmi=un(1,j)/(1+(abs(Ec(1,j)-Ec(2,j))/dx*un(1,j)/q/vsat_n(1,j))^pow_n(1,j))^(1/pow_n(1,j));
                Ecmi=Ec(1,j);%bar1;
                Nvmi=Nv(1,j);
                upmi=up(1,j)/(1+(abs(Ec(1,j)-Ec(2,j))/dx*up(1,j)/q/vsat_p(1,j))^pow_p(1,j))^(1/pow_p(1,j));
                Evmi=Ev(1,j);%bar1;
            else
                Ncmi=(Nc(i-1,j)+Nc(i,j))/2;
                unmi=(un(i-1,j)+un(i,j))/2;
                unmi=unmi/(1+(abs(Ec(i-1,j)-Ec(i,j))/dx*unmi/q/vsat_n(i,j))^pow_n(i,j))^(1/pow_n(i,j));
                Ecmi=(Ec(i-1,j)+Ec(i,j))/2;
                Nvmi=(Nv(i-1,j)+Nv(i,j))/2;
                upmi=(up(i-1,j)+up(i,j))/2;
                upmi=upmi/(1+(abs(Ec(i-1,j)-Ec(i,j))/dx*upmi/q/vsat_p(i,j))^pow_p(i,j))^(1/pow_p(i,j));
                Evmi=(Ev(i-1,j)+Ev(i,j))/2;               
            end
            if i+1>Nx
                Ncpi=Nc(Nx,j);
                unpi=un(Nx,j)/(1+(abs(Ec(Nx-1,j)-Ec(Nx,j))/dx*un(Nx,j)/q/vsat_n(Nx,j))^pow_n(Nx,j))^(1/pow_n(Nx,j));
                Ecpi=Ec(Nx,j);%bar1;
                Nvpi=Nv(Nx,j);
                uppi=up(Nx,j)/(1+(abs(Ec(Nx-1,j)-Ec(Nx,j))/dx*up(Nx,j)/q/vsat_p(Nx,j))^pow_p(Nx,j))^(1/pow_p(Nx,j));
                Evpi=Ev(Nx,j);%bar1;         
            else
                Ncpi=(Nc(i+1,j)+Nc(i,j))/2;
                unpi=(un(i+1,j)+un(i,j))/2;
                unpi=unpi/(1+(abs(Ec(i,j)-Ec(i+1,j))/dx*unpi/q/vsat_n(i,j))^pow_n(i,j))^(1/pow_n(i,j));
                Ecpi=(Ec(i+1,j)+Ec(i,j))/2;
                Nvpi=(Nv(i+1,j)+Nv(i,j))/2;
                uppi=(up(i+1,j)+up(i,j))/2;
                uppi=uppi/(1+(abs(Ec(i,j)-Ec(i+1,j))/dx*uppi/q/vsat_p(i,j))^pow_p(i,j))^(1/pow_p(i,j));
                Evpi=(Ev(i+1,j)+Ev(i,j))/2;                
            end
            if j-1<1
                Ncmj=Nc(i,1);
                unmj=un(i,1)/(1+(abs(Ec(i,1)-Ec(i,2))/dy*un(i,1)/q/vsat_n(i,1))^pow_n(i,1))^(1/pow_n(i,1));
                Ecmj=Ec(i,1);%bar3;
                Nvmj=Nv(i,1);
                upmj=up(i,1)/(1+(abs(Ec(i,1)-Ec(i,2))/dy*up(i,1)/q/vsat_p(i,1))^pow_p(i,1))^(1/pow_p(i,1));
                Evmj=Ev(i,1);%bar3;              
            else
                Ncmj=(Nc(i,j-1)+Nc(i,j))/2;
                unmj=(un(i,j-1)+un(i,j))/2;
                unmj=unmj/(1+(abs(Ec(i,j-1)-Ec(i,j))/dy*unmj/q/vsat_n(i,j))^pow_n(i,j))^(1/pow_n(i,j));
                Ecmj=(Ec(i,j-1)+Ec(i,j))/2;  
                Nvmj=(Nv(i,j-1)+Nv(i,j))/2;
                upmj=(up(i,j-1)+up(i,j))/2;
                upmj=upmj/(1+(abs(Ec(i,j-1)-Ec(i,j))/dy*upmj/q/vsat_n(i,j))^pow_p(i,j))^(1/pow_p(i,j));
                Evmj=(Ev(i,j-1)+Ev(i,j))/2;                 
            end 
            if j+1>Ny
                Ncpj=Nc(i,Ny);
                unpj=un(i,Ny)/(1+(abs(Ec(i,Ny-1)-Ec(i,Ny))/dy*un(i,Ny)/q/vsat_n(i,Ny))^pow_n(i,Ny))^(1/pow_n(i,Ny));
                Ecpj=Ec(i,Ny);%bar3;
                Nvpj=Nv(i,Ny);
                uppj=up(i,Ny)/(1+(abs(Ec(i,Ny-1)-Ec(i,Ny))/dy*up(i,Ny)/q/vsat_p(i,Ny))^pow_p(i,Ny))^(1/pow_p(i,Ny));
                Evpj=Ev(i,Ny);%bar3;                
            else
                Ncpj=(Nc(i,j+1)+Nc(i,j))/2;
                unpj=(un(i,j+1)+un(i,j))/2;
                unpj=unpj/(1+(abs(Ec(i,j)-Ec(i,j+1))/dy*unpj/q/vsat_n(i,j))^pow_n(i,j))^(1/pow_n(i,j));
                Ecpj=(Ec(i,j+1)+Ec(i,j))/2;  
                Nvpj=(Nv(i,j+1)+Nv(i,j))/2;
                uppj=(up(i,j+1)+up(i,j))/2;
                uppj=uppj/(1+(abs(Ec(i,j)-Ec(i,j+1))/dy*uppj/q/vsat_p(i,j))^pow_p(i,j))^(1/pow_p(i,j));
                Evpj=(Ev(i,j+1)+Ev(i,j))/2;             
            end 
               
            napi=unpi*Ncpi*kbT*exp(-Ecpi/kbT);
            nami=unmi*Ncmi*kbT*exp(-Ecmi/kbT);
            napj=unpj*Ncpj*kbT*exp(-Ecpj/kbT);
            namj=unmj*Ncmj*kbT*exp(-Ecmj/kbT); 
            papi=-uppi*Nvpi*kbT*exp(Evpi/kbT);
            pami=-upmi*Nvmi*kbT*exp(Evmi/kbT);
            papj=-uppj*Nvpj*kbT*exp(Evpj/kbT);
            pamj=-upmj*Nvmj*kbT*exp(Evmj/kbT);            
            m=findij(i,j,Nx,Ny);
            if m>0
                nLHS(m,m)=nLHS(m,m)+(-napi-nami)/dx^2+(-napj-namj)/dy^2;
                pLHS(m,m)=pLHS(m,m)+(-papi-pami)/dx^2+(-papj-pamj)/dy^2;
            end
            my=findij(i,j+1,Nx,Ny);
            if my>0
                nLHS(m,my)=nLHS(m,my)+napj/dy^2;
                pLHS(m,my)=pLHS(m,my)+papj/dy^2;
            elseif my==-4
                if i<lch1 | i>lch2
                    nLHS(m,m)=nLHS(m,m)+napj/dy^2;
                    pLHS(m,m)=pLHS(m,m)+papj/dy^2;
                else
                    nRHS(m)=nRHS(m)-napj/dy^2*exp(Ef4/kbT);
                    pRHS(m)=pRHS(m)-papj/dy^2*exp(-Ef4/kbT);
                end
            end
            my=findij(i,j-1,Nx,Ny);
            if my>0
                nLHS(m,my)=nLHS(m,my)+namj/dy^2;
                pLHS(m,my)=pLHS(m,my)+pamj/dy^2;
            elseif my==-3
                if i<lch1 | i>lch2
                    nLHS(m,m)=nLHS(m,m)+namj/dy^2;
                    pLHS(m,m)=pLHS(m,m)+pamj/dy^2;
                else
                    nRHS(m)=nRHS(m)-namj/dy^2*exp(Ef3/kbT);
                    pRHS(m)=pRHS(m)-pamj/dy^2*exp(-Ef3/kbT);
                end
            end
            my=findij(i+1,j,Nx,Ny);
            if my>0
                nLHS(m,my)=nLHS(m,my)+napi/dx^2;
                pLHS(m,my)=pLHS(m,my)+papi/dx^2;
            elseif my==-2
                if j<tch1 | j>tch2
                    nLHS(m,m)=nLHS(m,m)+napi/dx^2;
                    pLHS(m,m)=pLHS(m,m)+papi/dx^2;
                else
                    nRHS(m)=nRHS(m)-napi/dx^2*exp(Ef2/kbT);
                    pRHS(m)=pRHS(m)-papi/dx^2*exp(-Ef2/kbT);
                end
            end
            my=findij(i-1,j,Nx,Ny);
            if my>0
                nLHS(m,my)=nLHS(m,my)+nami/dx^2;
                pLHS(m,my)=pLHS(m,my)+pami/dx^2;
            elseif my==-1
                if j<tch1 | j>tch2
                    nLHS(m,m)=nLHS(m,m)+nami/dx^2;
                    pLHS(m,m)=pLHS(m,m)+pami/dx^2;
                else
                    nRHS(m)=nRHS(m)-nami/dx^2*exp(Ef1/kbT);
                    pRHS(m)=pRHS(m)-pami/dx^2*exp(-Ef1/kbT);
                end
            end
        end
     end
    phin=nLHS\nRHS;
    Efn=real(kbT*log(phin));
    Efn=reshape(Efn,[Ny,Nx]).';
    phip=pLHS\pRHS;
    Efp=real(-kbT*log(phip));
    Efp=reshape(Efp,[Ny,Nx]).';
end

