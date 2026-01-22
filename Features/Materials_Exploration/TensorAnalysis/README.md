# Tensor Analysis Feature

## Overview

Analyze and manipulate material properties using tensor mathematics, including stress-strain analysis, elastic properties, and higher-order property tensors.

## Inputs

- `tensor_type` (string): Type of tensor ('elastic', 'stress', 'strain', 'thermal', 'piezoelectric', 'magnetic')
- `tensor_data` (array): Tensor components (3x3, 6x6, or higher order)
- `operation` (string): Tensor operation ('diagonalize', 'rotate', 'contract', 'invert')
- `rotation_matrix` (array): Rotation matrix for tensor rotation (if applicable)
- `crystal_system` (string): Crystal symmetry for tensor reduction

## Outputs

- `eigenvalues` (array): Tensor eigenvalues
- `eigenvectors` (array): Tensor eigenvectors
- `rotated_tensor` (array): Rotated tensor components
- `invariants` (dict): Tensor invariants (trace, determinant, etc.)
- `principal_values` (array): Principal tensor values
- `symmetry_reduced_tensor` (array): Reduced tensor respecting symmetry
