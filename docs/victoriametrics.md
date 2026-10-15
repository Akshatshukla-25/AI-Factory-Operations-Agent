<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# VictoriaMetrics

Connect the observability component to an existing VictoriaMetrics service through
its Prometheus-compatible API. The metric discovery, instant query and historical
query tools support PromQL and MetricsQL. Mosaic does not install VictoriaMetrics.

## Metrics endpoint

Set `observability.prometheusUrl` to the query base URL. This setting accepts
Prometheus-compatible services, including VictoriaMetrics; no backend selector is
required.

| Deployment | Example base URL |
| --- | --- |
| Single-node VictoriaMetrics | `http://victoriametrics.monitoring.svc.cluster.local:8428` |
| VictoriaMetrics cluster | `http://vmselect.monitoring.svc.cluster.local:8481/select/0/prometheus` |

For a cluster, replace `0` with the intended tenant ID. Use the read endpoint
(`vmselect`), rather than `vminsert` or `vmagent`. Include the tenant path and any
proxy prefix, and omit `/api/v1`; the tools append the API paths themselves.
See the [VictoriaMetrics API examples](https://docs.victoriametrics.com/url-examples.html).

Use these values with your existing installation configuration:

```yaml
modules:
  observability:
    enabled: true
observability:
  prometheusUrl: http://vmselect.monitoring.svc.cluster.local:8481/select/0/prometheus
```

The endpoint must be reachable from the agent pod. Grafana credentials authenticate
Grafana requests, not direct metrics queries. Do not put credentials in the URL or
committed values.

## Grafana dashboards

VictoriaMetrics works with Grafana's Prometheus datasource and with the native
VictoriaMetrics datasource plugin. Configure Grafana to query the same backend and
tenant as `observability.prometheusUrl`, then use the datasource's actual UID.

For an existing Prometheus datasource, keep the default type:

```yaml
observability:
  grafanaDatasourceUid: metrics
  grafanaDatasourceType: prometheus
```

For Grafana's native VictoriaMetrics plugin:

```yaml
observability:
  grafanaDatasourceUid: victoria-metrics
  grafanaDatasourceType: victoriametrics-metrics-datasource
```

The Grafana administrator installs and configures the plugin; see the
[VictoriaMetrics Grafana integration](https://docs.victoriametrics.com/victoriametrics/integrations/grafana/datasource/).
Mosaic preserves this datasource type in dashboard panels, direct Grafana query
validation and frontend proxy validation. An explicit panel datasource overrides
the configured default. Loki panels can share a dashboard with either metrics
datasource type.

## Verify access

Ask Mosaic to list the available metric names, query a discovered metric, and
show its history for the past hour. Ask it to discover Grafana datasources before
creating a dashboard. Use the discovered UID and type for each panel.

MetricsQL extensions require a VictoriaMetrics backend. PromQL queries remain
supported, with the differences described in the
[MetricsQL documentation](https://docs.victoriametrics.com/victoriametrics/metricsql/).
