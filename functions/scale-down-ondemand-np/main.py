from operator import concat
from platform import node
from google.cloud import container_v1beta1
from google.cloud import compute_v1
import base64,json
#def handler(event, context): 
    #project_id =
    #location =
    #cluster =
    #on_demand_nodepool =
    #request = container_v1beta1.GetNodePoolRequest(
    #name=f"projects/{project_id}/locations/{location}/clusters/{cluster}/nodePools/{on_demand_nodepool}"
    #        )
    #response = client.get_node_pool(request=request)
    #ondemand_node_count = response.autoscaling.max_node_count
    #request = container_v1beta1.SetNodePoolSizeRequest(
    #        project_id=project_id,
    #        zone=location,
    #        cluster_id=cluster,
    #        node_pool_id=spot_nodepool,
    #        node_count=0
    #)
    #        # Make the request
    #response = client.set_node_pool_size(request=request)
    #return ()


def handler(request):
    request = request.get_data()
    try: 
        request_json = json.loads(request.decode())
    except ValueError as e:
        print(f"Error decoding JSON: {e}")
        return "JSON Error", 400
    nodepool = request_json.get("nodepool") 
    print(nodepool)

    # Create a client
    client = container_v1beta1.ClusterManagerClient()

    request = container_v1beta1.GetNodePoolRequest(name=nodepool)
    ondemand_node_count = response.autoscaling.max_node_count
    request = container_v1beta1.SetNodePoolSizeRequest(
    name=nodepool,
    node_count=ondemand_node_count-1 if (ondemand_node_count > 0) else 0)
    # Make the request
    response = client.set_node_pool_size(request=request)
    return 0