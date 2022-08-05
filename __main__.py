#create GKE Cluster and nodepools

import pulumi
import pulumi_gcp as gcp

gke_sa = gcp.serviceaccount.Account("gke_sa",
    account_id="gke-sa",
    display_name="GKE Service Account")
primary = gcp.container.Cluster("primary",
    location="us-central1",
    remove_default_node_pool=True,
    initial_node_count=1)
primary_spot_nodes = gcp.container.NodePool("primary-spot-nodes",
    location="us-central1",
    cluster=primary.name,
    autoscaling = gcp.container.NodePoolAutoscalingArgs(
        max_node_count = 1,
        min_node_count = 0
    ),
    node_count=0,
    node_config=gcp.container.NodePoolNodeConfigArgs(
        spot=True,
        machine_type="e2-micro",
        service_account=gke_sa.email,
        oauth_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    ))

ondemand_nodes = gcp.container.NodePool("on-demand-nodes",
    location="us-central1",
    cluster=primary.name,
    node_count=0,
    node_config=gcp.container.NodePoolNodeConfigArgs(
        machine_type="e2-micro",
        service_account=gke_sa.email,
        oauth_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    ))
