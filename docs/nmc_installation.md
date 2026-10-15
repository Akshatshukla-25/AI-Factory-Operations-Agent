# NMC Installation

This guide installs AI Factory Operations Agent on an NVIDIA Mission Control admin cluster. For upgrades, verification, LLM configuration, module reference, UI access, and headless usage, see the [shared Helm guide](installation.md).

For self-hosted inference on the separate GPU workload cluster, first follow [Self-hosted inference](#self-hosted-inference), then use its endpoint, served model name, and API key below. The bundled vLLM profile requires GPUs in the same cluster as the agent and should not be used on a GPU-free admin cluster.

## Install the agent

Run this flow from the Base Command Manager head node after setting `NGC_API_KEY`, `EXTERNAL_LLM_API_KEY`, `EXTERNAL_LLM_BASE_URL`, and `EXTERNAL_LLM_MODEL`. The endpoint, model, and API key must belong to the same OpenAI-compatible provider. For OpenAI, use `https://api.openai.com/v1` and a model available to that account.

Ask your NVIDIA contact to invite the email address you will use with NGC to the AI Factory Operations Agent `afoa-release` team in the private registry. Accept the invitation while signed in with that account; use a private browser window if another NGC account is already signed in. Then create an NGC personal API key from [NGC Setup > API Keys](https://org.ngc.nvidia.com/setup/api-keys), include the Private Registry service, and confirm that the account can pull the required private registry artifacts. NGC displays a newly generated key only once. Run the command in a login shell where `module load` is available.

The command selects the NMC `k8s-admin` cluster, connects AI Factory Operations Agent to the existing `kube-prometheus-stack` services, enables Slurm through Base Command Manager, and installs the AgentSandbox CRD and controller from the chart.

```bash
set -euo pipefail
module load kubernetes/k8s-admin

: "${NGC_API_KEY:?Set NGC_API_KEY to an NGC API key with private registry access}"
: "${EXTERNAL_LLM_API_KEY:?Set EXTERNAL_LLM_API_KEY for the selected provider}"
: "${EXTERNAL_LLM_BASE_URL:?Set EXTERNAL_LLM_BASE_URL for the selected provider}"
: "${EXTERNAL_LLM_MODEL:?Set EXTERNAL_LLM_MODEL for the selected provider}"
MOSAIC_NAMESPACE=${MOSAIC_NAMESPACE:-mosaic}
MOSAIC_CHART=oci://nvcr.io/0948643769302270/afoa-release/mosaic-stack
CLUSTER_MANAGER_HEAD_HOST=${CLUSTER_MANAGER_HEAD_HOST:-$(hostname -s)}
CLUSTER_MANAGER_SSH_KEY_PATH=${CLUSTER_MANAGER_SSH_KEY_PATH:-/root/.ssh/id_ecdsa}

test -r "$CLUSTER_MANAGER_SSH_KEY_PATH"
kubectl cluster-info >/dev/null
kubectl auth can-i create deployments -n "$MOSAIC_NAMESPACE" | grep -qx yes
kubectl -n prometheus get secret kube-prometheus-stack-grafana >/dev/null
cmsh -c 'wlm; list' | grep -qi slurm

printf '%s' "$NGC_API_KEY" | helm registry login nvcr.io \
  --username '$oauthtoken' \
  --password-stdin

kubectl create namespace "$MOSAIC_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$MOSAIC_NAMESPACE" create secret generic mosaic-external-llm \
  --from-literal=apiKey="$EXTERNAL_LLM_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$MOSAIC_NAMESPACE" create secret generic bcm-host-ssh-key \
  --from-file=id_ecdsa="$CLUSTER_MANAGER_SSH_KEY_PATH" \
  --dry-run=client -o yaml | kubectl apply -f -

GRAFANA_USERNAME=$(kubectl -n prometheus get secret kube-prometheus-stack-grafana -o jsonpath='{.data.admin-user}' | base64 -d)
GRAFANA_PASSWORD=$(kubectl -n prometheus get secret kube-prometheus-stack-grafana -o jsonpath='{.data.admin-password}' | base64 -d)
kubectl -n "$MOSAIC_NAMESPACE" create secret generic mosaic-grafana-auth \
  --from-literal=username="$GRAFANA_USERNAME" \
  --from-literal=password="$GRAFANA_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

# Remove --devel for the latest stable release, or replace it with --version 0.0.1 to pin that release.
helm upgrade --install mosaic "$MOSAIC_CHART" \
  --devel \
  -n "$MOSAIC_NAMESPACE" \
  --create-namespace \
  --set global.registryCredentials.create=true \
  --set-string global.registryCredentials.password="$NGC_API_KEY" \
  --set-json 'namespace.labels={"zarf.dev/agent":"ignore"}' \
  --set llm.mode=external \
  --set-string llm.external.baseUrl="$EXTERNAL_LLM_BASE_URL" \
  --set-string llm.external.model="$EXTERNAL_LLM_MODEL" \
  --set llm.external.existingSecret=mosaic-external-llm \
  --set observability.prometheusUrl=http://kube-prometheus-stack-prometheus.prometheus.svc.cluster.local:9090 \
  --set observability.grafanaUrl=http://kube-prometheus-stack-grafana.prometheus.svc.cluster.local/grafana \
  --set observability.grafanaDatasourceUid=prometheus \
  --set observability.grafanaAuth.existingSecret=mosaic-grafana-auth \
  --set modules.bcm.enabled=true \
  --set bcmMcp.enabled=true \
  --set bcmMcp.mode=ssh-adapter \
  --set-string bcmMcp.headHost="$CLUSTER_MANAGER_HEAD_HOST" \
  --set bcmMcp.hostSshKeySecretName=bcm-host-ssh-key \
  --set modules.slurm.enabled=true \
  --set modules.slurm.backend=auto \
  --reset-values \
  --wait \
  --timeout 12m
```

The command is a complete declaration and can be rerun unchanged. The SSH private key remains in the `bcm-host-ssh-key` Kubernetes Secret and is mounted only into the Base Command Manager adapter pod. On the first generic Base Command Manager MCP request, the adapter installs its matching remote server version on the Base Command Manager head automatically. With both modules enabled, the Slurm skill selects Base Command Manager WLM access instead of host-mounted vanilla evidence.

Before following the shared upgrade workflow in a new shell, run `module load kubernetes/k8s-admin` to select the NMC admin cluster.

## Self-hosted inference

NVIDIA Mission Control uses `k8s-admin` for management services and `k8s-user` for GPU workloads. See the [NMC Kubernetes installation guide](https://docs.nvidia.com/mission-control/docs/nmc-software-installation-guide/2.3.1/airgapped-installation/install-k8s.html). Confirm your site's actual GPU membership before installing inference.

Use two Helm releases: the standalone `helm/afoa-inference` example in `k8s-user`, and AI Factory Operations Agent in `k8s-admin`. Connect them through an authenticated HTTPS endpoint reachable from the admin cluster. Both services remain self-hosted. A namespace belongs to one cluster; a Helm release cannot schedule workloads in another cluster.

The bundled agent stack vLLM profiles require GPUs in the same cluster as the agent. Use this separate example when the admin cluster has no GPUs. Existing hosted or self-hosted endpoints can be used directly with the [agent installation flow](#install-the-agent).

### Prerequisites

- An existing `k8s-user` cluster with compatible GPUs, the NVIDIA device plugin, and the `nvidia` RuntimeClass. Set `runtimeClassName` to the runtime configured at your site, or an empty string when the default runtime supports GPUs.
- Capacity for the default Nemotron Super profile: one compatible GPU, 8 CPUs and 64 GiB requested host memory, and a 500 GiB persistent model cache. Check GPU memory, architecture, driver, and runtime compatibility against the [model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4). A single GPU resource does not guarantee that the model fits. Shared-memory usage counts toward the container's memory limit.
- A default StorageClass, or an explicit `modelCache.storageClassName`, supporting a 500 GiB ReadWriteOnce volume.
- Access to the pinned vLLM image and model weights. For restricted downloads, configure `modelToken.existingSecret` separately. Airgapped sites must provide an image mirror and a populated model cache.
- An internal ingress controller in `k8s-user`, internal DNS resolving its endpoint from `k8s-admin`, and a TLS Secret in the inference namespace. For a site CA, store its certificate in an admin-namespace Secret and set `llm.external.caCertificateSecret` (key `ca.crt`, configurable with `caCertificateKey`). The agent and compatibility proxy add this CA to their normal trust stores. Routing and firewall rules must allow admin-cluster pods to reach the endpoint on port 443. Configure the ingress controller's HTTPS redirect and streaming timeouts for your environment; the chart does not install a controller or create certificates.
- In Run:ai-managed environments, ensure the target namespace has sufficient GPU quota.

### Deploy inference in `k8s-user`

Run from a checkout of this repository at the release or commit you intend to deploy. Keep site values in your own tracked configuration; keep secrets out of Git. The example chart is included in source, separately from the published agent stack OCI artifact.

Select the GPU cluster and inspect its resources:

```bash
module load kubernetes/k8s-user
kubectl config current-context
kubectl get nodes -o custom-columns='NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu'
kubectl get runtimeclass
kubectl get storageclass
kubectl get ingressclass
```

Create `inference-values.yaml` with your site's ingress class, DNS name, and existing TLS Secret. The following names are placeholders:

```yaml
ingress:
  enabled: true
  className: nginx
  host: inference.example.com
  tlsSecretName: inference-tls
# Set only when choosing a non-default StorageClass.
# modelCache:
#   storageClassName: your-storage-class
# For mixed GPU nodes, select compatible hardware using your site's labels.
# nodeSelector:
#   nvidia.com/gpu.product: NVIDIA-B200
```

Create an inference API key and save it in your protected credential store. Use the same key for the inference server and the agent client. The inference key is separate from NGC registry and Hugging Face download credentials.

```bash
read -rsp 'Self-hosted inference API key: ' EXTERNAL_LLM_API_KEY; echo
kubectl create namespace afoa-inference --dry-run=client -o yaml | kubectl apply -f -
kubectl -n afoa-inference create secret generic afoa-inference-auth \
  --from-literal=apiKey="$EXTERNAL_LLM_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install afoa-inference ./helm/afoa-inference \
  -n afoa-inference \
  -f inference-values.yaml \
  --wait \
  --timeout 2h
```

The release creates one vLLM StatefulSet, a persistent model cache, a ClusterIP Service, and the configured ingress. It installs no agent, UI, or cluster integrations. The image is pinned to the same digest as the bundled Super profile. The `/v1` API uses a key from the existing Secret; the ingress routes only `/v1`. Keep the backend Service on a trusted network: vLLM's API key does not protect every server endpoint. See [vLLM security guidance](https://docs.vllm.ai/en/latest/usage/security/).

The first download and model initialization can exceed 30 minutes. Cached weights still require first-start GPU kernel compilation; CPU activity during that phase does not mean the inference API is ready. This example retains resources after a Helm timeout so events and logs remain available. Check progress before retrying:

```bash
kubectl -n afoa-inference get pods,pvc,service,ingress
kubectl -n afoa-inference describe pod afoa-inference-0
kubectl -n afoa-inference get events --sort-by=.lastTimestamp
kubectl -n afoa-inference logs afoa-inference-0 -c vllm --tail=100
```

`Pending` with insufficient GPUs, CPU, or memory is a scheduling problem. An unbound PVC is a storage problem. Download progress followed by model loading is expected initialization. Keep the cache size unchanged during upgrades; the StatefulSet volume claim template cannot be resized by a normal Helm upgrade.

### Connect the agent in `k8s-admin`

Set the endpoint and served model name:

```bash
export EXTERNAL_LLM_BASE_URL='https://inference.example.com/v1'
export EXTERNAL_LLM_MODEL='nemotron-super-120b'
module load kubernetes/k8s-admin
kubectl config current-context
```

Do not use the user-cluster Service's `*.svc.cluster.local` name across clusters. Use the internal ingress hostname. Keep `/v1` in the base URL and use `servedModelName` as the client model, rather than the download repository name.

For a new agent installation, continue with the existing [agent installation flow](#install-the-agent), using these variables and the inference key. That guide stores the provider key in the admin cluster and installs with `llm.mode=external`. “External” identifies an endpoint outside the agent release and includes self-hosted inference.

For an existing installation, update only its provider settings, retaining enabled modules and site configuration. Use the same chart version already installed, or the explicitly selected upgrade version. `AGENT_CHART_VERSION` below must be set to that version; `AGENT_CHART` is the chart reference from the NMC guide.

First check the new endpoint from the existing agent pod, streaming the self-hosted key through stdin without changing its configuration:

```bash
printf '%s' "$EXTERNAL_LLM_API_KEY" | \
kubectl -n "${AGENT_NAMESPACE:?Set the existing agent namespace}" exec -i deployment/openclaw -c gateway -- \
  node --input-type=module -e '
let key = "";
for await (const chunk of process.stdin) key += chunk;
const response = await fetch(`${process.argv[1].replace(/\/$/, "")}/chat/completions`, {
  method: "POST",
  headers: {Authorization: `Bearer ${key}`, "Content-Type": "application/json"},
  body: JSON.stringify({model: process.argv[2], messages: [{role: "user", content: "Reply with ready."}], max_tokens: 32}),
  signal: AbortSignal.timeout(120000),
});
console.log(`Inference check: HTTP ${response.status}`);
if (!response.ok) process.exit(1);
' "$EXTERNAL_LLM_BASE_URL" "$EXTERNAL_LLM_MODEL"
```

Proceed after HTTP 200. Create a separate client Secret so the existing provider's Secret stays intact until the switch:

```bash
: "${AGENT_CHART_VERSION:?Set the intended chart version}"
: "${EXTERNAL_LLM_API_KEY:?Load the self-hosted key from your protected store}"
: "${AGENT_NAMESPACE:?Set the existing agent namespace}"
: "${AGENT_RELEASE:?Set the existing agent Helm release}"
: "${AGENT_CHART:?Set the existing agent chart reference}"
kubectl -n "$AGENT_NAMESPACE" create secret generic afoa-inference-client \
  --from-literal=apiKey="$EXTERNAL_LLM_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

helm upgrade "$AGENT_RELEASE" "$AGENT_CHART" \
  --version "$AGENT_CHART_VERSION" \
  -n "$AGENT_NAMESPACE" \
  --reuse-values \
  --set llm.mode=external \
  --set-string llm.external.baseUrl="$EXTERNAL_LLM_BASE_URL" \
  --set-string llm.external.model="$EXTERNAL_LLM_MODEL" \
  --set llm.external.existingSecret=afoa-inference-client \
  --set llm.external.apiKeySecretKey=apiKey \
  --wait \
  --timeout 12m

unset EXTERNAL_LLM_API_KEY
```

This changes the configured provider and restarts affected agent pods. Switching from bundled `llm.mode=vllm` also removes that release's bundled inference workload; verify the new endpoint first. The separate inference release and enabled agent modules remain independently managed. Rotating an existing Secret's key also requires restarting the consumers to reload their environment; updating only a Secret does not automatically restart pods.

### Verify from the admin-cluster agent pod

After installing or switching, verify authenticated model discovery and a short completion from the actual agent pod. This uses the key already mounted into the pod without printing it:

```bash
kubectl -n "${AGENT_NAMESPACE:?Set the existing agent namespace}" exec -i deployment/openclaw -c gateway -- node --input-type=module - <<'JS'
const base = process.env.OPENCLAW_VLLM_BASE_URL.replace(/\/$/, '');
const headers = {
  Authorization: `Bearer ${process.env.VLLM_API_KEY}`,
  'Content-Type': 'application/json',
};
for (const [path, options] of [
  ['/models', {}],
  ['/chat/completions', {method: 'POST', body: JSON.stringify({
    model: 'nemotron-super-120b',
    messages: [{role: 'user', content: 'Reply with ready.'}],
    max_tokens: 32,
  })}],
]) {
  const response = await fetch(`${base}${path}`, {
    ...options, headers, signal: AbortSignal.timeout(120000),
  });
  console.log(`${path}: HTTP ${response.status}`);
  if (!response.ok) process.exit(1);
}
JS
```

Use your configured served model name in the completion check if you changed the default. HTTP 200 for both requests establishes DNS, routing, TLS trust, authentication, and basic inference from the admin cluster. Then ask a short question through the agent UI to verify the full agent path. TLS errors require correcting certificate trust, timeouts require checking routing or server readiness, and 401 responses indicate mismatched keys.
