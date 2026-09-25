# Run the EMOS webapp on the VM

This guide runs the EMOS frontend and Flask backend on the VM while the
model services run in Kubernetes namespace `eidf204ns`.

## 1. Check the model services

```bash
kubectl get pods -n eidf204ns
```

The services used by the webapp are:

- `emos-mattergen` - GPU service
- `emos-chgnet` - GPU service
- `emos-gbfs` - CPU service
- `emos-gbfs2d` - CPU service
- `emos-mattersim` - GPU service, when GPU quota is available

## 2. Forward model service ports

Open one terminal for each command and leave them running:

```bash
kubectl port-forward -n eidf204ns service/emos-mattergen 8100:8000
```

```bash
kubectl port-forward -n eidf204ns service/emos-gbfs 8200:8000
```

```bash
kubectl port-forward -n eidf204ns service/emos-gbfs2d 8201:8000
```

```bash
kubectl port-forward -n eidf204ns service/emos-chgnet 8400:8000
```

If MatterSim is running, forward it too:

```bash
kubectl port-forward -n eidf204ns service/emos-mattersim 8300:8000
```

A port-forward must remain open while the backend is using that model.

## 3. Start the EMOS backend

In a new terminal:

```bash
cd ~/EMOS
source emos_env/bin/activate

export MATTERGEN_API_URL=http://localhost:8100
export GBFS_PRED_API_URL=http://localhost:8200
export GBFS2D_API_URL=http://localhost:8201
export CHGNET_API_URL=http://localhost:8400
export MATTERSIM_API_URL=http://localhost:8300

python backend/app.py
```

The backend listens on port `5001` by default. Test it from another terminal:

```bash
curl http://localhost:5001/api/health
```

If MatterSim is not running, leave `MATTERSIM_API_URL` unset and do not use
MatterSim nodes in the webapp until its GPU pod is available.

## 4. Start the frontend

In another terminal:

```bash
cd ~/EMOS
python3 -m http.server 8080 --bind 0.0.0.0
```

The static frontend listens on port `8080`.

## 5. Open the webapp in VS Code

In the VS Code Ports panel, forward these ports from the VM:

- `8080` - frontend
- `5001` - backend

Open the forwarded URL for port `8080`, then open `index.html` if needed.

The browser talks to the Flask backend. The Flask backend talks to the
Kubernetes model services through the local port-forwards.

```text
Browser -> Flask backend:5001 -> Kubernetes model service -> result
```

## 6. Basic service checks

```bash
curl http://localhost:8200/ready
curl http://localhost:8201/ready
curl http://localhost:8400/health
curl http://localhost:8100/health
```

Expected model services should return an HTTP success response. Stop a
port-forward with `Ctrl+C` when it is no longer needed.
