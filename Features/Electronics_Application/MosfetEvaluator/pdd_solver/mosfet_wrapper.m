%%Author: Chien-Ting Tung, PhD at University of California, Berkeley
%%Modified: Python-callable wrapper — reads all inputs from inputs.mat,
%%          writes J, Q, Vgs, Vds to outputs.mat. No hardcoded parameters.
%%reference: http://yrwu-wk.ee.ntu.edu.tw/index.php/teaching-course/

%% ── Load inputs written by the Python wrapper ───────────────────────────────
load(inputs_mat_path);   % injected by caller: contains all variables below
% Expected variables (see MosfetSolver.py for full list):
%   T, dx, dy, L, sd, Tox, Tch, phig, phisd
%   channel_doping, sd_doping
%   Vgs_start, Vgs_stop, Nvg, Vds_start, Vds_stop, Nvd
%   ch_Nc, ch_Nv, ch_ep, ch_un, ch_up, ch_xi, ch_Eg
%   ch_vsat_n, ch_vsat_p, ch_pow_n, ch_pow_p
%   ins_Nc, ins_Nv, ins_ep, ins_un, ins_up, ins_xi, ins_Eg
%   ins_vsat_n, ins_vsat_p, ins_pow_n, ins_pow_p

%% ── Physical constants ───────────────────────────────────────────────────────
q   = 1.6e-19;
kb  = 1.380649e-23;
ep0 = 8.853e-12;
kbT = kb * T;

%% ── Grid ─────────────────────────────────────────────────────────────────────
Ns = ceil(sd / dx);
Nc_grid = ceil(L / dx);
Nd = ceil(sd / dx);
Nx = Ns + Nc_grid + Nd;
lch1 = Ns + 1;        % first x-index of channel
lch2 = Ns + Nc_grid;  % last  x-index of channel

No = ceil(Tox / dy);
Nt = ceil(Tch / dy);
Ny = No * 2 + Nt;
tch1 = No + 1;        % top    y-index of channel
tch2 = No + Nt;       % bottom y-index of channel

x = dx * linspace(0, Nx, Nx).';
y = dy * linspace(0, Ny, Ny).';

%% ── Material arrays (insulator everywhere, channel region overwritten) ───────
Nc  = ones(Nx, Ny) * ins_Nc;    Nc(:, tch1:tch2)  = ch_Nc;
Nv  = ones(Nx, Ny) * ins_Nv;    Nv(:, tch1:tch2)  = ch_Nv;
un  = ones(Nx, Ny) * ins_un;    un(:, tch1:tch2)   = ch_un;
up  = ones(Nx, Ny) * ins_up;    up(:, tch1:tch2)   = ch_up;
vsat_n = ones(Nx,Ny)*ins_vsat_n; vsat_n(:,tch1:tch2) = ch_vsat_n;
vsat_p = ones(Nx,Ny)*ins_vsat_p; vsat_p(:,tch1:tch2) = ch_vsat_p;
pow_n  = ones(Nx,Ny)*ins_pow_n;  pow_n(:,tch1:tch2)  = ch_pow_n;
pow_p  = ones(Nx,Ny)*ins_pow_p;  pow_p(:,tch1:tch2)  = ch_pow_p;
Eg  = ones(Nx, Ny) * q * ins_Eg; Eg(:, tch1:tch2)  = q * ch_Eg;
EP  = ones(Nx, Ny) * ep0 * ins_ep; EP(:, tch1:tch2) = ep0 * ch_ep;
xi  = ones(Nx, Ny) * q * ins_xi; xi(:, tch1:tch2)   = q * ch_xi;

%% ── Doping ───────────────────────────────────────────────────────────────────
NB = zeros(Nx, Ny);
NB(lch1:lch2,   tch1:tch2) = 1e6 * channel_doping;   % channel (p-type: negative)
NB(1:lch1-1,    tch1:tch2) = 1e6 * sd_doping;         % source  (n+)
NB(lch2+1:Nx,   tch1:tch2) = 1e6 * sd_doping;         % drain   (n+)

%% ── Bias sweeps ──────────────────────────────────────────────────────────────
Vgs = linspace(Vgs_start, Vgs_stop, Nvg);
Vds = linspace(Vds_start, Vds_stop, Nvd);

J = zeros(Nvg, Nvd);
Q = zeros(Nvg, Nvd);

%% ── Main simulation loop ─────────────────────────────────────────────────────
for i = 1:Nvg
    for j = 1:Nvd
        Ef1 = 0;
        Ef2 = -q * Vds(j);
        Ef3 = -q * Vgs(i);
        Ef4 = -q * Vgs(i);
        Ec1 = q * phisd + Ef1;
        Ec2 = q * phisd + Ef2;
        Ec3 = q * phig  + Ef3;
        Ec4 = q * phig  + Ef4;

        [Ec, Efn, Efp] = solve(q, kbT, Nx, Ny, dx, dy, NB, EP, Eg, ...
            un, up, vsat_n, vsat_p, pow_n, pow_p, Nc, Nv, xi, ...
            tch1, tch2, lch1, lch2, Ec1, Ec2, Ec3, Ec4, Ef1, Ef2, Ef3, Ef4);

        Ev = Ec - Eg;
        n  = Nc .* exp((Efn - Ec) / kbT);
        p  = Nv .* exp((Ev  - Efp) / kbT);

        Jn = un ./ (1 + (abs(gradient(Ec.').')  / dx .* un  / q ./ vsat_n).^pow_n).^(1./pow_n) ...
             .* n .* gradient(Efn.').'/dx;
        Jp = up ./ (1 + (abs(gradient(Ec.').')  / dx .* up  / q ./ vsat_p).^pow_p).^(1./pow_p) ...
             .* p .* gradient(Efp.').'/dx;

        J(i,j) = -sum(Jn(Nx, tch1:tch2) + Jp(Nx, tch1:tch2)) * dy;
        Q(i,j) = -q * sum(n(lch1:lch2, tch1:tch2) ...
                         - p(lch1:lch2, tch1:tch2) ...
                         - NB(lch1:lch2, tch1:tch2), 'all') * dx * dy;
    end
end

%% ── Save outputs for Python to read ─────────────────────────────────────────
save(outputs_mat_path, 'J', 'Q', 'Vgs', 'Vds', 'x', 'y');
