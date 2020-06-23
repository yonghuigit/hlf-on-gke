#!/bin/sh
NAMESPACE=gke-hlf-ns
echo "Cleaning up"
helm uninstall prometheus --namespace $NAMESPACE
helm uninstall grafana --namespace $NAMESPACE
echo "Installing"
helm install prometheus stable/prometheus --namespace $NAMESPACE -f prometheus_values.yaml
helm install grafana stable/grafana --namespace $NAMESPACE --set service.type=NodePort
