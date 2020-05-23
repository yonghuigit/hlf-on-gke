from kubernetes import client as k8s_client, config as k8s_config
import googleapiclient.discovery
import os
import yaml


def get_service_to_domain_mapping(load_balance_nodes, ca_enabled):
    cn_suffix = '-cluster-nodeport'
    with open('../fabric-config/crypto-config.yaml') as crypto_config_file:
        crypto_config = yaml.load(crypto_config_file, Loader=yaml.FullLoader)
        orderer_orgs = crypto_config['OrdererOrgs']
        peer_orgs = crypto_config['PeerOrgs']
        service_to_domain_mapping = {}
        orgs = orderer_orgs + peer_orgs
        for org in orgs:
            org_name = org['Name'].lower()
            org_domain = org['Domain'].lower()
            if 'orderer' in org_name:
                if load_balance_nodes:
                    service_to_domain_mapping[org_name + cn_suffix] = org_domain
            else:
                if load_balance_nodes:
                    service_to_domain_mapping[org_name + cn_suffix] = 'peer.' + org_domain
                if ca_enabled:
                    service_to_domain_mapping[org_name + '-ca' + cn_suffix] = 'ca.' + org_domain

            for host in org['Specs']:
                host_name = host['Hostname']
                service_to_domain_mapping[org_name + '-' + host_name + cn_suffix] = host_name + '.' + org_domain
        return service_to_domain_mapping


def get_instance_in_zones(project, zones, default_pool):
    compute = googleapiclient.discovery.build('compute', 'v1')
    instances_in_zones = {}
    one_instance = {'network': '', 'instanceNetworkTag': ''}
    for zone in zones:
        instance_groups = compute.instanceGroups().list(project=project, zone=zone).execute()
        for instance_group in instance_groups['items']:
            ig_name = instance_group['name']
            if default_pool in ig_name:
                instances = compute.instanceGroups().listInstances(project=project, zone=zone,
                                                                   instanceGroup=ig_name).execute()
                for instance in instances['items']:
                    instance_url = instance['instance']
                    last_slash_ind = instance_url.rindex('/')
                    instance_name = instance_url[last_slash_ind + 1:]
                    instances_in_zones[zone] = instance_url

    instance_detail = compute.instances().get(project=project, zone=zone, instance=instance_name).execute()
    one_instance['network'] = instance_detail['networkInterfaces'][0]['network']
    one_instance['instanceNetworkTag'] = instance_detail['tags']['items']
    return [instances_in_zones, one_instance]


def get_named_ports(namespace):
    k8s_config.load_kube_config()
    k8s_v1 = k8s_client.CoreV1Api()
    api_response = k8s_v1.list_namespaced_service(namespace, watch=False)

    named_ports = []
    firewall_ports = []

    for i in api_response.items:
        if not i.spec.ports:
            continue
        for j in i.spec.ports:
            if not j.node_port:
                continue
            named_port = {'name': 'port' + str(j.node_port), 'port': j.node_port}
            named_ports.append(named_port)
            firewall_ports.append(j.node_port)
    return [named_ports, firewall_ports]


def get_backend_and_healthcheck_config(namespace):
    k8s_config.load_kube_config()
    k8s_v1 = k8s_client.CoreV1Api()
    api_response = k8s_v1.list_namespaced_service(namespace, watch=False)

    backend_config = []
    health_check_config = {}
    for i in api_response.items:
        if not i.spec.ports:
            continue
        for j in i.spec.ports:
            if not j.node_port:
                continue
            backend_config.append({i.metadata.name: j.node_port})
            if j.port == 8443 or '-ca-cluster-' in i.metadata.name:
                health_check_config[i.metadata.name] = j.node_port

    return [health_check_config, backend_config]


''' set this up according to the projects'''
############################################
with open('hlflb-config.yaml') as config_file, \
     open('../hlf-network/values.yaml') as values_file, \
     open('hlflb.yaml', 'w') as outputfile:
    config = yaml.load(config_file, Loader=yaml.FullLoader)
    values = yaml.load(values_file, Loader=yaml.FullLoader)
    # if using service account, need to set this environment variable
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config['resources'][0]['properties']['gcpCredentialFile']
    proj = config['resources'][0]['properties']['project']
    zos = config['resources'][0]['properties']['zones']
    cluster_name = config['resources'][0]['properties']['clusterName']
    defp = cluster_name + '-default-pool'

    ns = values['hlfNetworkNamespace']
    lb_nodes = values['hlfLoadBalancePeerNodes']
    ca_enabled = values['hlfCAEnabled']
    ############################################

    named_ports_ret = get_named_ports(ns)
    config['resources'][0]['properties']['instanceGroupNamedPorts'] = named_ports_ret[0]
    config['resources'][0]['properties']['firewallPorts'] = named_ports_ret[1]

    be_and_hc_config = get_backend_and_healthcheck_config(ns)
    config['resources'][0]['properties']['healthChecks'] = be_and_hc_config[0]
    config['resources'][0]['properties']['backends'] = be_and_hc_config[1]

    inst_in_zone_ret = get_instance_in_zones(proj, zos, defp)
    instances_zones = inst_in_zone_ret[0]
    config['resources'][0]['properties']['instanceInZones'] = instances_zones

    network_details = inst_in_zone_ret[1]
    config['resources'][0]['properties']['network'] = network_details['network']
    config['resources'][0]['properties']['instanceNetworkTag'] = network_details['instanceNetworkTag']

    serv_to_domain_map = get_service_to_domain_mapping(lb_nodes, ca_enabled)
    config['resources'][0]['properties']['servToDomainMapping'] = serv_to_domain_map

    documents = yaml.dump(config, outputfile)

