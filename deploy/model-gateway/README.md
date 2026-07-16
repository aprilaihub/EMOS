# Minimal Model Gateway (No Core Code Changes)

This folder supports a minimal 2-service Render deployment.

## What is included

- `gateway_api.py`: mounts existing model APIs under path prefixes
  - `/mattergen`
  - `/mattersim`
  - `/chgnet`
  - `/gbfs`
- `Dockerfile`: single private model-gateway container
- `render.hybrid.yaml`: separate opt-in Render blueprint

## Important

This setup intentionally does **not** modify existing EMOS source files.

## Deploy

1. Create a new Render Blueprint instance using `render.hybrid.yaml`.
2. Wait for both services to finish deploying.
3. Validate gateway endpoints:
   - `/health`
   - `/mattergen/health`
   - `/mattersim/health`
   - `/chgnet/health`
   - `/gbfs/health`

## Notes

- This image is heavy because it includes multiple model stacks.
- If build conflicts occur, pin versions inside the gateway Dockerfile.
- Keep your current production blueprint unchanged until this hybrid instance is stable.
