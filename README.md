# hlf-on-gke
## Create a GKE cluster
## Set context for the cluster
```
gcloud beta container clusters get-credentials xxxxx --region xxxxxx --project xxxxxx
```
## Clone this project locally
```
git clone https://github.com/yonghuigit/hlf-on-gke.git  
cd hlf-on-gke
```
## Set up helm/tiller
```
kubectl create -f kube-common/rbac-config.yaml  
helm init --service-account tiller --history-max 200
```
## Generate crypto and configuration materials
```
./fabric-config/generate.sh
```
## Get the clusterIP for kube-dns and set hlfKubeDNSSvcIP
```
export KUBE_DNS_IP=$(kubectl get --namespace kube-system -o jsonpath='{.spec.clusterIP}{"\n"}' services kube-dns); echo $KUBE_DNS_IP
```
## Register a static ip
```
gcloud compute addresses create hlf-load-balancer-static-ip --global
export HLF_LB_STATIC_IP=`gcloud compute addresses describe hlf-load-balancer-static-ip --global --format='value(address)'`; echo $HLF_LB_STATIC_IP
```
## Run helm install with
```
helm install hlf-network -f ./hlf-network/crypto-config.yaml -f hlf-network/values.yaml  -n hlf-network-prod --set hlfKubeDNSSvcIP=$KUBE_DNS_IP --set hlfLBStaticIP=$HLF_LB_STATIC_IP
```
## Continue to follow the instructions output at the end of the helm install
