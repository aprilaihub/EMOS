%%Author: Chien-Ting Tung, PhD at University of California, Berkeley
%%reference: http://yrwu-wk.ee.ntu.edu.tw/index.php/teaching-course/

function [m]=findij(i,j,Nx,Ny)
    m=(i-1)*Ny+j;
    if i<1
        m=-1;
    elseif i>Nx
        m=-2;
    end
    if j<1
        m=-3;
    elseif j>Ny
        m=-4;
    end  
end
