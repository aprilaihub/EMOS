# EMOS Kubernetes deployment

These manifests target the GPU Kubernetes environment described in
`~/EIDF_tutorial`. They deploy the Docker-backed model services in the
existing `eidf204ns` namespace. Replace the example image names with images
available to the cluster before applying them.

## Build and publish images

The login VM does not provide Docker or `nvidia-smi`, so build these images
with the project's image builder or CI and push them to a registry visible to
the cluster:

```text
atishdixit16/emos-mattergen:gpu
atishdixit16/emos-chgnet:gpu
atishdixit16/emos-mattersim:gpu
atishdixit16/emos-gbfs:cpu
atishdixit16/emos-gbfs2d:cpu
```

The build contexts are the EMOS root for GBFS/GBFS2D and each model's
`docker` directory for MatterGen, CHGNet, and MatterSim.

## Deploy

The Kueue queue label is taken from the VM tutorial. Apply the namespace and
services first, then verify GPU allocation and health:

```bash
kubectl apply -f k8s/gpu/models.yaml
kubectl get pods -n eidf204ns -w
kubectl describe pod -n eidf204ns -l emos.ai/gpu-model=true
```

The GPU services request one GPU each. GBFS and GBFS2D are deployed without a
GPU because their models use scikit-learn/LightGBM and matminer.

## Connect the EMOS backend

When the backend is deployed in the same namespace, use these URLs:

```text
MATTERGEN_API_URL=http://emos-mattergen:8000
CHGNET_API_URL=http://emos-chgnet:8000
MATTERSIM_API_URL=http://emos-mattersim:8000
GBFS_PRED_API_URL=http://emos-gbfs:8000
GBFS2D_API_URL=http://emos-gbfs2d:8000
```

Before connecting the backend, test each service through a temporary debug pod
or port-forward and confirm `/health` and `/info` respond.