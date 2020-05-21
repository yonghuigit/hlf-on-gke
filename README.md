# Install a Hyperledger Fabric network on a Google Kubernetes Engine Cluster

## 1. Install command line tools locally - Ubuntu 18.04
### gcloud, kubectl, helm, go
```
sudo snap install google-cloud-sdk --classic
gcloud version
sudo snap install kubectl --classic
kubectl version
sudo snap install helm --classic
helm version
sudo snap install go --classic
go version
```

## 2. Install Hyperledger Fabric command line tools locally.
```
curl -sSL http://bit.ly/2ysbOFE | bash -s 2.1.0
export PATH=$PATH:~/fabric-samples/bin
# check that Fabric command line tools are on your path
peer version
```

## 3. Register your own domain if you don't yet have one.

## 4. Create a GKE cluster using GCP Console and then
### Log in to gcloud from shell  
```
# type this and follow instructions to authenticate
gcloud auth login
```
### Set context for the cluster. 
```
# Use your own CLUSTER_NAME, REGION, PROJECT_NAME below
# set default project
gcloud config set project PROJECT_NAME
gcloud beta container clusters get-credentials CLUSTER_NAME --region REGION --project PROJECT_NAME
```
## 5. Clone this project locally
```
git clone https://github.com/yonghuigit/hlf-on-gke.git  
cd hlf-on-gke
```
## 6. Note: if you are using Helm 2, set up helm/tiller on the cluster. Skip this step if you are using Helm 3
```
kubectl create -f kube-common/rbac-config.yaml  
helm init --service-account tiller --history-max 200
```
## 7. Generate crypto materials and genesis block 
### modify fabric-config/setvars.sh to set the variables to the correct values, e.g. use your own registered domain 
```
### export SYS_CHANNEL_NAME=ibc-sys-channel
### export ORDERER_ORG_DOMAIN=orderer.yourdomain.com
### export ORG1_DOMAIN=org1.yourdomain.com
### export ORG2_DOMAIN=org2.yourdomain.com
```
### Execute the script to generate crypto materials and genesis block 
```
./fabric-config/generate.sh
```
## 8. Get the clusterIP for kube-dns and set hlfKubeDNSSvcIP. GKE v1.13.x, v1.14.x uses kube-dns rather than core-dns. Our script will install core-dns and will use custom stub domains to redirect domain lookup for *.yourdomain.com to core-dns. core-dns will rewrite the custom domain names to cluster local domain names. Then it will redirect back to kube-dns to resolve to cluster IP addresses for the orderer, peer nodes. 
```
export KUBE_DNS_IP=$(kubectl get --namespace kube-system -o jsonpath='{.spec.clusterIP}{"\n"}' services kube-dns); echo $KUBE_DNS_IP
```
## 9. Register a static ip to be used for the load balancer and as the targe IP for all the domain names of the nodes. The ingress/load balancer create host and path rules to connect the URLs to the correct backends.
```
gcloud compute addresses create hlf-load-balancer-static-ip --global
```
## 10. If you are using Helm 2, run helm install with
```
helm install hlf-network -f ./hlf-network/crypto-config.yaml -f hlf-network/values.yaml  -n hlf-network-prod --set hlfKubeDNSSvcIP=$KUBE_DNS_IP --set hlfLBStaticIPName=hlf-load-balancer-static-ip
```
## 11. If you are using Helm 3, use this command instead
```
helm install hlf-network-prod hlf-network -f ./hlf-network/crypto-config.yaml -f hlf-network/values.yaml --set hlfKubeDNSSvcIP=$KUBE_DNS_IP --set hlfLBStaticIPName=hlf-load-balancer-static-ip
```
## 12. Continue to follow the instructions printed at the end of the helm install. It will look something like this. Make sure to use the domain names printed.
```
NOTES:
# Helm install finished.
# Let's work on setting up the url rewrite in coredns so the orderer/peer nodes can find each other
export INTERNAL_CORE_DNS_IP=$(kubectl get --namespace kube-system -o jsonpath='{.spec.clusterIP}{"\n"}' services internal-dns); echo $INTERNAL_CORE_DNS_IP
sed -i -e s/INTERNAL_CORE_DNS_IP/$INTERNAL_CORE_DNS_IP/g kube-common/kube-dns-configmap-update.yaml
# Change HLF_STUB_DOMAIN to use your own domain, such as example.com, mycompany.net, et. al.
export HLF_STUB_DOMAIN=example.com
sed -i -e s/HLF_STUB_DOMAIN/$HLF_STUB_DOMAIN/g kube-common/kube-dns-configmap-update.yaml

# Verify the values have been replaced correctly
cat kube-common/kube-dns-configmap-update.yaml
# Be sure to add additional lines for additional stubdomains to point to the same IP
# Then
kubectl apply -f kube-common/kube-dns-configmap-update.yaml

# Get the reserved static IP
gcloud compute addresses describe hlf-load-balancer-static-ip --global --format='value(address)'

# In your domain DNS management tool, make sure to point following domains to the static ip
orderer.yourdomain.com
ord-0.orderer.yourdomain.com
ord-1.orderer.yourdomain.com
ord-2.orderer.yourdomain.com
peer.org1.yourdomain.com
peer-0.org1.yourdomain.com
peer-1.org1.yourdomain.com
peer-2.org1.yourdomain.com
peer.org2.yourdomain.com
peer-0.org2.yourdomain.com
peer-1.org2.yourdomain.com
peer-2.org2.yourdomain.com
ca.org1.yourdomain.com
ca.org2.yourdomain.com

# Now Run GCP Deployment Script for the load balancer
sudo apt update
sudo apt install python3 python3-dev python3-venv python-pip
cd hlf-load-balancer
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install --upgrade wheel
pip install kubernetes
pip install google-api-python-client
# Double Check gcloud setting
gcloud auth list
gcloud config list
# Change values in hlflb-config.yaml
python3 setup.py
gcloud deployment-manager deployments list
gcloud deployment-manager deployments delete hlf-load-balancer
gcloud deployment-manager deployments create hlf-load-balancer --config=hlflb.yaml

# https://cloud.google.com/docs/authentication/getting-started

# Wait for the load balancer to show up and the certificates to be provisioned. This might take 15 minutes.
```

## 13. Check in GCP Console -> Kubernetes Engine to make sure all Workloads, Services & Ingress are displaying green.

## 14. Check in GCP Console -> Network services -> Load balancing

## 15. Set up a channel named 'ibcchannel-dev' in the network that we just created
```
cd fabric-config
./channel-setup.sh ibcchannel-dev
```

## 16. Install and instantiate chaincode fabcar on the channel 'ibcchannel-dev'
```
./chaincode-fabcar.sh ibcchannel-dev
```
