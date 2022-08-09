#create GKE Cluster and nodepools

import pulumi
import pulumi_gcp as gcp
from pulumi import Output

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

#create log metric to detect no scale up in Spot MIG
spot_mig_no_scale_up_metric = gcp.logging.Metric("SpotMigNoScaleUpMetric",
    filter=Output.concat('resource.type=k8s_cluster AND resource.labels.location= us-central1 AND resource.labels.cluster_name=',primary.name,' AND severity>=DEFAULT AND jsonPayload.noDecisionStatus.noScaleUp.napFailureReason.messageId=no.scale.up.nap.disabled'),
    metric_descriptor=gcp.logging.MetricMetricDescriptorArgs(
        metric_kind="DELTA",
        value_type="INT64",
    ))