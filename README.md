# hlf-on-gke
# create a GKE cluster
gcloud beta container --project "yongssandbox" clusters create "blockchain" --region "us-west1" --no-enable-basic-auth --release-channel "regular" --machine-type "n1-standard-2" --image-type "COS" --disk-type "pd-standard" --disk-size "100" --metadata disable-legacy-endpoints=true --scopes "https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append" --num-nodes "1" --enable-stackdriver-kubernetes --enable-ip-alias --network "projects/yongssandbox/global/networks/default" --subnetwork "projects/yongssandbox/regions/us-west1/subnetworks/default" --default-max-pods-per-node "110" --addons HorizontalPodAutoscaling,HttpLoadBalancing --enable-autoupgrade --enable-autorepair --tags "allow-ssh-from-home-and-itrade"
# set context for the cluster
gcloud beta container clusters get-credentials blockchain --region us-west1 --project yongssandbox
# set up helm/tiller
kubectl create -f kube-common/rbac-config.yaml
helm init --service-account tiller --history-max 200

# get the clusterIP for kube-dns and --set hlfKubeDNSSvcIP to overwrite value in hlf-network/values.yaml
export KUBE_DNS_IP=$(kubectl get --namespace kube-system -o jsonpath='{.spec.clusterIP}{"\n"}' services kube-dns); echo $KUBE_DNS_IP

helm install hlf-network -f ./hlf-network/crypto-config.yaml -f hlf-network/values.yaml  -n hlf-network-prod --set hlfKubeDNSSvcIP=$KUBE_DNS_IP
# continue to follow the instructions output at the end of the helm install
