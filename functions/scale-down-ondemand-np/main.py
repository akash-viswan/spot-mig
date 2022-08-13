from operator import concat
from google.cloud import container_v1beta1
from google.cloud import compute_v1
import base64,json
def handler(event, context): 
    

    request = container_v1beta1.GetNodePoolRequest(
    name=f"projects/{project_id}/locations/{location}/clusters/{cluster}/nodePools/{on_demand_nodepool}"
            )
    response = client.get_node_pool(request=request)
    ondemand_node_count = response.autoscaling.max_node_count
    request = container_v1beta1.SetNodePoolSizeRequest(
            project_id=project_id,
            zone=location,
            cluster_id=cluster,
            node_pool_id=spot_nodepool,
            node_count=0
    )
            # Make the request
    response = client.set_node_pool_size(request=request)
    return ()