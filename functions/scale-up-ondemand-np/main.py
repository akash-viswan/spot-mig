from operator import concat
from google.cloud import container_v1beta1
from google.cloud import compute_v1
import base64,json
def handler(event, context): 
    
    if 'data' in event:
        data = json.loads(base64.b64decode(event['data']).decode('utf-8'))
        print(data)
        #print('"{}" received!'.format(name))
        cluster = data['resource']['labels']['cluster_name']
        location     = data['resource']['labels']['location']
        project_id     = data['resource']['labels']['project_id']
        spot_nodepool = data['jsonPayload']['noDecisionStatus']['noScaleUp']['skippedMigs'][0]['mig']['nodepool']
        on_demand_nodepool = '-'.join(spot_nodepool.split('-')[0:-1])+'-ondemand'
    
        # Create a client
        client = container_v1beta1.ClusterManagerClient()

        # Initialize request argument(s)
        request = container_v1beta1.GetNodePoolRequest(
            name=f"projects/{project_id}/locations/{location}/clusters/{cluster}/nodePools/{spot_nodepool}"
        )
        # Make the request
        response = client.get_node_pool(request=request)
        max_spot_mig_count = response.autoscaling.max_node_count
        print(response.name,response.autoscaling.max_node_count)

        #Calculate spot instance node count
        spot_node_count = 0
        spot_node_zones = 0
        compute_client = compute_v1.InstanceGroupsClient()
        for instance_group_url in response.instance_group_urls:
            names = instance_group_url.split('/')
            #print(names)
            request = compute_v1.types.compute.GetInstanceGroupRequest(
	            project=names[6],
	            zone=names[8],
	            instance_group=names[10],
	            )
            response=compute_client.get(request=request)
            #print(response)
            spot_node_count += response.size
            spot_node_zones += 1	
        print("spot nodes= ",spot_node_count)
        #doing this for the demo, IRL node_count//spot_node_zones < max_spot_mig_count is a state were Spot instances are not available.
        #Also max scaling of ondemand mig can be same as max of spot mig
        if spot_node_count//spot_node_zones == max_spot_mig_count:
            request = container_v1beta1.GetNodePoolRequest(
            name=f"projects/{project_id}/locations/{location}/clusters/{cluster}/nodePools/{on_demand_nodepool}"
            )
            response = client.get_node_pool(request=request)
            ondemand_node_count = response.autoscaling.max_node_count
            request = container_v1beta1.SetNodePoolSizeRequest(
                name=f"projects/{project_id}/locations/{location}/clusters/{cluster}/nodePools/{on_demand_nodepool}",
                node_count=ondemand_node_count+1 if (ondemand_node_count+1 < 5) else 5
            )
            # Make the request
            response = client.set_node_pool_size(request=request)
    return ()