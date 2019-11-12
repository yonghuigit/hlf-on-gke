# hlf-on-gke
# create a GKE cluster
# set context for the cluster
gcloud beta container clusters get-credentials xxxxx --region xxxxxx --project xxxxxx
# set up helm/tiller
kubectl create -f kube-common/rbac-config.yaml
helm init --service-account tiller --history-max 200

# get the clusterIP for kube-dns and --set hlfKubeDNSSvcIP to overwrite value in hlf-network/values.yaml
export KUBE_DNS_IP=$(kubectl get --namespace kube-system -o jsonpath='{.spec.clusterIP}{"\n"}' services kube-dns); echo $KUBE_DNS_IP

helm install hlf-network -f ./hlf-network/crypto-config.yaml -f hlf-network/values.yaml  -n hlf-network-prod --set hlfKubeDNSSvcIP=$KUBE_DNS_IP
# continue to follow the instructions output at the end of the helm install
