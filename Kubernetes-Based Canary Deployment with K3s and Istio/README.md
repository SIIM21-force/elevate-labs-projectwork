# 🚀 Kubernetes-Based Canary Deployment with K3s and Istio

[![Kubernetes](https://img.shields.io/badge/Kubernetes-K3s-blue?logo=kubernetes)](https://k3s.io/)
[![Istio](https://img.shields.io/badge/Service%20Mesh-Istio-466BB0?logo=istio)](https://istio.io/)
[![Helm](https://img.shields.io/badge/Helm-v3-0F1689?logo=helm)](https://helm.sh/)
[![Container Engine](https://img.shields.io/badge/Container-Podman-892CA0?logo=podman)](https://podman.io/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://www.python.org/)

A production-grade implementation of **Progressive Delivery** using **Istio Service Mesh** on a **K3s (Kubernetes)** cluster. This project demonstrates intelligent Layer 7 (L7) traffic splitting between a stable production version (`v1.0`) and a new canary release (`v2.0`), enabling zero-downtime rollouts, automated rollback capabilities, and live traffic validation.

---

## 📌 Table of Contents
- [Architecture Overview](#-architecture-overview)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Repository Structure](#-repository-structure)
- [Step-by-Step Setup & Execution](#-step-by-step-setup--execution)
  - [1. Istio Service Mesh Installation](#1-istio-service-mesh-installation)
  - [2. Building and Containerizing the Applications](#2-building-and-containerizing-the-applications)
  - [3. Deploying Kubernetes Workloads](#3-deploying-kubernetes-workloads)
  - [4. Configuring Ingress & Canary Routing Rules](#4-configuring-ingress--canary-routing-rules)
  - [5. Traffic Splitting Verification (80/20 Test)](#5-traffic-splitting-verification-8020-test)
  - [6. Promotion and Instant Rollback](#6-promotion-and-instant-rollback)
- [Why Canary with Istio over Standard Rolling Updates?](#-why-canary-with-istio-over-standard-rolling-updates)
- [Deliverables & Results](#-deliverables--results)

---

## 🏗️ Architecture Overview

```
                      User Requests (HTTP)
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Istio Ingress Gateway │
                    │   (Port 80 / Ingress) │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │    VirtualService     │
                    │   (Traffic Splitter)  │
                    └───────┬───────┬───────┘
                      80%   │       │  20%
              ┌─────────────┘       └─────────────┐
              ▼                                   ▼
   ┌──────────────────────┐            ┌──────────────────────┐
   │   DestinationRule    │            │   DestinationRule    │
   │     Subset: v1       │            │     Subset: v2       │
   └──────────┬───────────┘            └──────────┬───────────┘
              │                                   │
              ▼                                   ▼
 ┌─────────────────────────┐         ┌─────────────────────────┐
 │  canary-app-v1 (Stable) │         │  canary-app-v2 (Canary) │
 │   2 Replicas (v1.0)     │         │    1 Replica (v2.0)     │
 │ [App Container + Envoy] │         │ [App Container + Envoy] │
 └─────────────────────────┘         └─────────────────────────┘
```

---

## ✨ Key Features

- **Granular Traffic Control:** Route external traffic probabilistically (e.g., 80% to stable `v1.0`, 20% to canary `v2.0`) regardless of replica counts.
- **Service Mesh Envoy Sidecars:** Automatic proxy injection intercepting pod communication for transparent telemetry and routing.
- **Resource Constraints:** Best-practice CPU and memory limits/requests configured for all containers.
- **Instant Rollback:** Zero pod redeployments needed—traffic is diverted in sub-seconds by updating the `VirtualService` manifest.
- **Decoupled Deployment from Release:** Workloads are deployed safely to production before any live user traffic is routed to them.

---

## 🛠️ Tech Stack

| Tool / Component | Version / Role | Purpose |
| :--- | :--- | :--- |
| **Kubernetes (K3s)** | v1.36+ (Rancher Desktop) | Lightweight container orchestration cluster |
| **Istio Service Mesh** | v1.25+ | Ingress gateway, Envoy sidecar proxies, and traffic management |
| **Helm** | v3 | Declarative package management for Istio control plane |
| **Podman** | v6.1+ | Rootless OCI container builder and registry client |
| **Python / Flask** | Python 3.11 | Microservice exposing version-aware JSON endpoints |
| **Docker Hub** | `sam2127/canary-app` | Remote image repository |

---

## 📂 Repository Structure

```text
sample-devops-project-1/
├── app.py                  # Lightweight Python/Flask app returning version metadata
├── Dockerfile              # Multi-stage/lean Python 3.11 container image definition
├── app-deployments.yaml    # K8s Deployments (v1 & v2) and shared ClusterIP Service
├── istio-routing.yaml      # Istio Gateway, DestinationRule, and VirtualService
├── pyproject.toml          # Project configuration & dependencies
└── README.md               # Project documentation
```

---

## 🚀 Step-by-Step Setup & Execution

### 1. Istio Service Mesh Installation
Deploy Istio into the K3s cluster using Helm charts:

```powershell
# Add Istio Helm repository
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm repo update

# Install base CRDs
helm install istio-base istio/base -n istio-system --create-namespace

# Install Istio control plane (istiod)
helm install istiod istio/istiod -n istio-system

# Install Istio Ingress Gateway
helm install istio-ingress istio/gateway -n istio-system

# Enable automatic Envoy sidecar injection on the default namespace
kubectl label namespace default istio-injection=enabled
```

Verify the control plane and ingress gateway are running:
```powershell
kubectl get pods -n istio-system
```

---

### 2. Building and Containerizing the Applications
Containerize both versions of the application using **Podman**:

```powershell
# Authenticate with container registry
podman login docker.io

# 1. Build and push Stable Version (v1.0)
podman build -t docker.io/sam2127/canary-app:v1 .
podman push docker.io/sam2127/canary-app:v1

# 2. Build and push Canary Version (v2.0)
# (Update APP_VERSION to "v2.0" in app.py)
podman build -t docker.io/sam2127/canary-app:v2 .
podman push docker.io/sam2127/canary-app:v2
```

---

### 3. Deploying Kubernetes Workloads
Apply [app-deployments.yaml](app-deployments.yaml) containing the deployments for `canary-app-v1`, `canary-app-v2`, and the unified service:

```powershell
kubectl apply -f app-deployments.yaml
```

Verify that pods have 2/2 containers ready (Application container + Envoy sidecar proxy):
```powershell
kubectl get pods -l app=canary-app
```

Output:
```text
NAME                             READY   STATUS    RESTARTS   AGE
canary-app-v1-98b55564b-rkgfg    2/2     Running   0          18m
canary-app-v1-98b55564b-svqdh    2/2     Running   0          18m
canary-app-v2-6df6df7f89-ddcnz   2/2     Running   0          18m
```

---

### 4. Configuring Ingress & Canary Routing Rules
Apply [istio-routing.yaml](istio-routing.yaml) to configure the Gateway, DestinationRule, and VirtualService:

```powershell
kubectl apply -f istio-routing.yaml
```

Key configuration elements:
- **`Gateway`**: Listens on port 80 for incoming external HTTP requests.
- **`DestinationRule`**: Maps incoming traffic to subsets `v1` and `v2` matching pod labels `version: v1` and `version: v2`.
- **`VirtualService`**: Sets the traffic split to **80% v1** and **20% v2**:
  ```yaml
  http:
  - route:
    - destination:
        host: canary-app-service
        subset: v1
      weight: 80
    - destination:
        host: canary-app-service
        subset: v2
      weight: 20
  ```

---

### 5. Traffic Splitting Verification (80/20 Test)

To route requests into the cluster from Windows without occupying a foreground terminal, start a background port-forwarding job:

```powershell
Start-Job -Name "k8s-tunnel" -ScriptBlock { kubectl port-forward svc/istio-ingress -n istio-system 8080:80 }
```

Run an automated 50-request test loop to verify traffic distribution:

```powershell
1..50 | ForEach-Object {
    $res = Invoke-RestMethod -Uri "http://localhost:8080"
    Write-Host "Request $_ : $($res.message)"
}
```

#### Sample Test Output:
```text
Request 1  : Hello from App version v1.0!
Request 2  : Hello from App version v1.0!
Request 3  : Hello from App version v2.0!  <-- Canary
Request 4  : Hello from App version v1.0!
Request 5  : Hello from App version v1.0!
...
Request 48 : Hello from App version v1.0!
Request 49 : Hello from App version v2.0!  <-- Canary
Request 50 : Hello from App version v1.0!
```
*Observed Distribution: ~80% Stable (v1.0) and ~20% Canary (v2.0).*

---

### 6. Promotion and Instant Rollback

#### A. Promotion to 100% Canary
Once performance and health metrics are verified, promote `v2` to receive 100% of traffic by updating [istio-routing.yaml](istio-routing.yaml):
```yaml
    - destination:
        host: canary-app-service
        subset: v1
      weight: 0
    - destination:
        host: canary-app-service
        subset: v2
      weight: 100
```
Apply with `kubectl apply -f istio-routing.yaml`. All users seamlessly receive version `v2.0` with **zero downtime**.

#### B. Instant Rollback (In Case of Defects)
If unexpected errors or latency spikes occur in `v2`, restore traffic to `v1` immediately:
```yaml
    - destination:
        host: canary-app-service
        subset: v1
      weight: 100
    - destination:
        host: canary-app-service
        subset: v2
      weight: 0
```
Traffic is re-routed back to stable in milliseconds without restarting or recreating pods.

---

## 🧠 Why Canary with Istio over Standard Rolling Updates?

| Feature | Standard Kubernetes Rolling Update | Istio Canary Deployment |
| :--- | :--- | :--- |
| **Traffic Ratio Control** | Dictated strictly by replica count (e.g., 1 canary out of 4 pods = fixed 25%) | Independently controlled by weights (e.g., 99% / 1% or 80% / 20%) |
| **Blast Radius** | High; newly scheduled pods take traffic immediately | Minimal; small percentage of requests validate the release first |
| **Rollback Speed** | Requires pulling old image and rebuilding pods (seconds to minutes) | Sub-second configuration update via Envoy routing rules |
| **L7 Routing Capabilities** | Layer 4 round-robin only | Advanced L7 routing (headers, cookies, HTTP methods, user IDs) |

---

## 📊 Deliverables & Results

- **Deployment Manifests:** Fully documented in [app-deployments.yaml](app-deployments.yaml) and [istio-routing.yaml](istio-routing.yaml).
- **Traffic Logs:** 80/20 request distribution verified via automated PowerShell testing.
- **Canary Strategy:** Demonstrated progressive rollout, traffic shifting, and sub-second rollback.
- **Teardown Command:**
  ```powershell
  kubectl delete -f istio-routing.yaml
  kubectl delete -f app-deployments.yaml
  Stop-Job -Name "k8s-tunnel" -ErrorAction SilentlyContinue
  ```

