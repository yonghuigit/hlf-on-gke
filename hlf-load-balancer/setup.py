from kubernetes import client as k8s_client, config as k8s_config
import googleapiclient.discovery
import os, yaml


def get_instance_in_zones(project, zones, default_pool):
    compute = googleapiclient.discovery.build('compute', 'v1')
    instances_in_zones = {}
    for zone in zones:
        instance_groups = compute.instanceGroups().list(project=project, zone=zone).execute()
        for instance_group in instance_groups['items']:
            ig_name = instance_group['name']
            if default_pool in ig_name:
                instances = compute.instanceGroups().listInstances(project=project, zone=zone,
                                                                   instanceGroup=ig_name).execute()
                for instance in instances['items']:
                    instances_in_zones[zone] = instance['instance']
    return instances_in_zones


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
            # firewall_ports = firewall_ports + str(j.node_port) + ','
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
with open('hlflb-config.yaml') as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config['resources'][0]['properties']['gcpCredentialFile']
    proj = config['resources'][0]['properties']['project']
    zos = config['resources'][0]['properties']['zones']
    ns = config['resources'][0]['properties']['namespace']
    defp = config['resources'][0]['properties']['defaultPool']
    ############################################

    named_ports_ret = get_named_ports(ns)
    config['resources'][0]['properties']['instanceGroupNamedPorts'] = named_ports_ret[0]
    config['resources'][0]['properties']['firewallPorts'] = named_ports_ret[1]

    be_and_hc_config = get_backend_and_healthcheck_config(ns)
    config['resources'][0]['properties']['healthChecks'] = be_and_hc_config[0]
    config['resources'][0]['properties']['backends'] = be_and_hc_config[1]

    instances_zones = get_instance_in_zones(proj, zos, defp)
    config['resources'][0]['properties']['instanceInZones'] = instances_zones

    with open('hlflb.yaml', 'w') as outputfile:
        documents = yaml.dump(config, outputfile)

