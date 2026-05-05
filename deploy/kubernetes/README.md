# Kubernetes deployment

Reference manifests for running politics-dashboard on Kubernetes. They assume:

- A namespace (defaults to `politics`).
- An `nginx`-style Ingress, Gateway API, or Service of type LoadBalancer in
  front of the `politics-ui` Service. None of that is included here — wire it
  to whatever you already use.
- A SOPS/sealed-secrets workflow for `politics-secrets`. The committed
  manifest is a placeholder.

## Layout

```
deploy/kubernetes/
├── 00-namespace.yaml
├── 10-deployment-api.yaml
├── 11-deployment-ui.yaml
├── 20-service-api.yaml
├── 21-service-ui.yaml
├── 30-configmap.yaml         # politics-config (config.yaml)
├── 40-secret.example.yaml    # politics-secrets — DO NOT commit your real one
└── kustomization.yaml
```

## Customize

1. Replace `40-secret.example.yaml` with your encrypted secret. It must carry
   the env vars your `config.yaml` references — at minimum `LLM_API_KEY`, plus
   `FRESHRSS_API_PASSWORD` if using FreshRSS, plus any `X_*` overrides if you
   set `twitter.handles_env_prefix: X`.
2. Edit `30-configmap.yaml` (`config.yaml` payload). Same schema as
   `config.example.yaml` at the repo root.
3. Edit the `images:` block in `kustomization.yaml` to point at your registry
   and tag.
4. `kubectl apply -k deploy/kubernetes/` (or sync via ArgoCD/Flux).
