COMPUTE_URL_BASE = 'https://www.googleapis.com/compute/v1/projects/'

def generate_config(context):
    """Generate YAML resource configuration."""
    config = {'resources': []}
    project =  context.properties['project']
    lb_ip = context.properties['loadBalancerIP']
    zone_config = context.properties['zones']
    named_ports = context.properties['instanceGroupNamedPorts']
    instance_in_zones = context.properties['instanceInZones']
    health_checks = context.properties['healthChecks']
    backends = context.properties['backends']
    inst_net_tag = context.properties['instanceNetworkTag']
    firewall_ports = context.properties['firewallPorts']
    firewall_source_range = context.properties['firewallSourceRange']
    service_to_domain_mapping = context.properties['servToDomainMapping']
    network_name = context.properties['network']

    network_url = COMPUTE_URL_BASE + project + '/global/networks/' + network_name
    description = ' created for L7 load balancer/hyperledger fabric'

    """Generate Instance Groups - one per zone - and associate instances from default pool to the new IG"""
    for zone in ['us-west1-a', 'us-west1-b', 'us-west1-c']:
        ig_name = 'ig-resource-for-' + context.env['name'] + '-' + zone
        instance_group = {
            'name': ig_name,
            'type': 'compute.v1.instanceGroup',
            'properties': {
                'description': 'instance group' + description,
                'namedPorts': named_ports,
                'zone': zone
            }
        }

        config['resources'].append(instance_group)

        add_instance = {
            'name': ig_name + '-add-instance',
            'action': 'gcp-types/compute-v1:compute.instanceGroups.addInstances',
            'properties': {
                    'zone': zone,
                    'instanceGroup': '$(ref.{}.name)'.format(ig_name),
                    'instances': [{
                        'instance': instance_in_zones[zone]
                    }]
            }
        }
        config['resources'].append(add_instance)

    """Generate Health Checks"""
    for service, port in health_checks.items():
        health_check = {
            'name': 'hc-resource-for-' + context.env['name'] + '-' + str(port),
            'type': 'compute.v1.healthCheck',
            'properties': {
                'description': 'health check' + description + '-' + service,
                'checkIntervalSec': 60,
                'timeoutSec': 60,
                'healthyThreshold': 1,
                'unhealthyThreshold': 10
            }
        }
        if '-ca-cluster-' in service:
            health_check['properties']['type'] = 'HTTPS'
            health_check['properties']['httpsHealthCheck'] = {}
            health_check['properties']['httpsHealthCheck']['requestPath'] = '/cainfo'
            health_check['properties']['httpsHealthCheck']['port'] = port
        else:
            health_check['properties']['type'] = 'HTTP'
            health_check['properties']['httpHealthCheck'] = {}
            health_check['properties']['httpHealthCheck']['requestPath'] = '/healthz'
            health_check['properties']['httpHealthCheck']['port'] = port

        config['resources'].append(health_check)

    """Generate Backends"""
    for service_port in backends:
        for service, port in service_port.items():
            health_check_id = health_checks[service]
            health_check_name = 'hc-resource-for-' + context.env['name'] + '-' + str(health_check_id)
            protocol = 'HTTP2'
            if '-ca-cluster-' in service:
                protocol = 'HTTPS'
            elif port == health_check_id:
                protocol = 'HTTP'

            backend = {
                'name': 'be-' + service + '-' + context.env['name'] + '-' + str(port),
                'type': 'compute.v1.backendService',
                'properties': {
                    'description': 'backend service' + description + '-' + service + '-' + protocol,
                    'loadBalancingScheme': 'EXTERNAL',
                    'logConfig': {
                        'enable': True
                    },
                    'portName': 'port' + str(port),
                    'protocol': protocol,
                    'sessionAffinity': 'NONE',
                    'timeoutSec': 600,
                    'connectionDraining': {
                        'drainingTimeoutSec': 60
                    },
                    'backends': [],
                    'healthChecks': ['$(ref.' + health_check_name + '.selfLink)']
                }
            }
            for zone in zone_config:
                backend['properties']['backends'].append({
                    'balancingMode': 'RATE',
                    'capacityScaler': 1.0,
                    'group': '$(ref.{}.selfLink)'.format('ig-resource-for-hlf-load-balancer-' + zone),
                    'maxRatePerInstance': 1.0
                })

        config['resources'].append(backend)

    """Generate URL Map"""
    # get one default backend for the entire url map
    for service, port in health_checks.items():
        if '-ca-cluster-' not in service:
            um_default_service_name = 'be-' + service + '-' + context.env['name'] + '-' + str(port)
            break

    url_map_name = 'um-resource-for-' + context.env['name']
    url_map = {
        'name': url_map_name,
        'type': 'compute.v1.urlMap',
        'properties': {
            'description': 'urlmap' + description,
            'defaultService': '$(ref.' + um_default_service_name + '.selfLink)',
            'hostRules': [],
            'pathMatchers': []
        }
    }

    for service, port in health_checks.items():
        host_rule = {
            'hosts': [service_to_domain_mapping[service]],
            'pathMatcher': 'pm-for-' + service
        }
        url_map['properties']['hostRules'].append(host_rule)

        be_name = 'be-' + service + '-' + context.env['name'] + '-' + str(port)
        path_matcher = {
            'defaultService': '$(ref.' + be_name + '.selfLink)',
            'name': 'pm-for-' + service,
            'pathRules': []
        }

        path_rule1 = {
            'paths': ['/healthz', '/metrics'],
            'service': '$(ref.' + be_name + '.selfLink)'
        }

        if '-ca-cluster-' in service:
            path_rule1['paths'] = ['/cainfo', '/*']

        path_matcher['pathRules'].append(path_rule1)

        if '-ca-cluster-' not in service:
            path_rule2 = {
                'paths': ['/*']
            }
            for service_port in backends:
                for service2, port2 in service_port.items():
                    if service2 == service and port2 != port:
                        be_name2 = 'be-' + service + '-' + context.env['name'] + '-' + str(port2)
                        path_rule2['service'] = '$(ref.' + be_name2 + '.selfLink)'
            path_matcher['pathRules'].append(path_rule2)

        url_map['properties']['pathMatchers'].append(path_matcher)

    config['resources'].append(url_map)

    """Generate Google Managed SSL Certificate"""
    ssl_cert_name = 'sslcert-resource-for-' + context.env['name']
    ssl_cert = {
        'name': ssl_cert_name,
        'type': 'gcp-types/compute-beta:sslCertificates',
        'properties': {
            'type': 'MANAGED',
            'managed': {
                'domains': []
            }
        }
    }

    for serv, domain in service_to_domain_mapping.items():
        ssl_cert['properties']['managed']['domains'].append(domain)

    config['resources'].append(ssl_cert)

    """Generate Target Proxy"""
    target_proxy_name = 'tp-resource-for-' + context.env['name']
    target_proxy = {
        'name': target_proxy_name,
        'type': 'compute.v1.targetHttpsProxy',
        'properties': {
            'urlMap': '$(ref.' + url_map_name + '.selfLink)',
            'sslCertificates': ['$(ref.' + ssl_cert_name + '.selfLink)']
        }
    }
    config['resources'].append(target_proxy)

    """Generate Forwarding Rule"""
    forwarding_rule = {
        'name': 'fw-resource-for-' + context.env['name'],
        'type': 'compute.v1.globalForwardingRule',
        'properties': {
            "IPAddress": lb_ip,
            'IPProtocol': 'TCP',
            'portRange': 443,
            'target': '$(ref.' + target_proxy_name + '.selfLink)'
        }
    }
    config['resources'].append(forwarding_rule)

    """Generate Firewall Rule"""
    firewall_rule = {
        'name': inst_net_tag + '-' + context.env['name'],
        'type': 'compute.v1.firewall',
        'properties': {
            'network': network_url,
            'allowed': [{
                'IPProtocol': 'TCP',
                'ports': firewall_ports
            }],
            'sourceRanges': firewall_source_range,
            'targetTags': [inst_net_tag]
        }
    }

    config['resources'].append(firewall_rule)

    return config
