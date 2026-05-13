%%Author: Chien-Ting Tung, PhD at University of California, Berkeley
%%reference: http://yrwu-wk.ee.ntu.edu.tw/index.php/teaching-course/

function [A,bd]=getA2d(Nx,Ny,dx,dy,EP,xi,tch1,tch2,lch1,lch2,Ec1,Ec2,Ec3,Ec4)
    A=sparse(Nx*Ny,Nx*Ny);
    bd=sparse(Nx*Ny,1);
    for i=1:Nx
        for j=1:Ny
            if i-1<1
                EPmi=EP(i,j);
                DEcmi=0;
            else
                EPmi=(EP(i-1,j)+EP(i,j))/2;
                DEcmi=-xi(i,j)+xi(i-1,j);
            end
            if j-1<1
                EPmj=EP(i,j);
                DEcmj=0;
            else
                EPmj=(EP(i,j-1)+EP(i,j))/2;
                DEcmj=-xi(i,j)+xi(i,j-1);
            end            
            if i+1>Nx
                EPpi=EP(i,j);
                DEcpi=0;
            else
                EPpi=(EP(i+1,j)+EP(i,j))/2;
                DEcpi=-xi(i+1,j)+xi(i,j);
            end
            if j+1>Ny
                EPpj=EP(i,j);
                DEcpj=0;
            else
                EPpj=(EP(i,j+1)+EP(i,j))/2;
                DEcpj=-xi(i,j+1)+xi(i,j);
            end
            m=findij(i,j,Nx,Ny);
            if m>0
                A(m,m)=A(m,m)+(-EPmi-EPpi)/dx^2+(-EPmj-EPpj)/dy^2;
                bd(m,1)=bd(m,1)-EPmi*DEcmi/dx^2+EPpi*DEcpi/dx^2-EPmj*DEcmj/dy^2+EPpj*DEcpj/dy^2;   
            end
            my=findij(i,j+1,Nx,Ny);
            if my>0
                A(m,my)=A(m,my)+EPpj/dy^2;
            elseif my==-4
                if i>=lch1 & i<=lch2
                    bd(m,1)=bd(m,1)-Ec4/dy^2*EPpj; %contact
                %elseif i<lch1
                %    bd(m,1)=bd(m,1)-Ec1/dy^2*EPpj; %contact
                %elseif i>lch2
                %    bd(m,1)=bd(m,1)-Ec2/dy^2*EPpj; %contact                 
                else
                    A(m,m)=A(m,m)+EPpj/dy^2; %Neumann
                end
            end
            my=findij(i,j-1,Nx,Ny);
            if my>0
                A(m,my)=A(m,my)+EPmj/dy^2;
            elseif my==-3
                if i>=lch1 & i<=lch2
                    bd(m,1)=bd(m,1)-Ec3/dy^2*EPmj; %contact
                %elseif i<lch1
                %    bd(m,1)=bd(m,1)-Ec1/dy^2*EPmj; %contact
                %elseif i>lch2
                %    bd(m,1)=bd(m,1)-Ec2/dy^2*EPmj; %contact                     
                else
                    A(m,m)=A(m,m)+EPmj/dy^2; %Neumann
                end
            end
            my=findij(i+1,j,Nx,Ny);
            if my>0
                A(m,my)=A(m,my)+EPpi/dx^2;
            elseif my==-2
                if j>=tch1 & j<=tch2
                    bd(m,1)=bd(m,1)-Ec2/dx^2*EPpi; %contact                    
                else
                    A(m,m)=A(m,m)+EPpi/dx^2; %Neumann
                end
            end
            my=findij(i-1,j,Nx,Ny);
            if my>0
                A(m,my)=A(m,my)+EPmi/dx^2;
            elseif my==-1
                if j>=tch1 & j<=tch2
                    bd(m,1)=bd(m,1)-Ec1/dx^2*EPmi; %contact
                else
                    A(m,m)=A(m,m)+EPmi/dx^2; %Neumann
                end                
            end
        end
    end    
end
