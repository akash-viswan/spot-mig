#create GKE Cluster and nodepools
from urllib import request
import pulumi_gcp as gcp
from pulumi import Output
import pulumi
import base64

def string_to_base64(message):
    message_bytes=message.encode('ascii')
    return base64.b64encode(message_bytes)

config = pulumi.Config('gcp')
proj = config.get('project')
location = config.get('region')

gke_sa = gcp.serviceaccount.Account("gke_sa",
    account_id="gke-sa",
    display_name="GKE Service Account")

gke_sa_perm = gcp.projects.IAMMember("gke-sa-perm",
    member=Output.concat('serviceAccount:',gke_sa.email),
    project = proj,
    role="roles/container.clusterAdmin")
gke_sa_perm2 = gcp.projects.IAMMember("gke-sa-perm2",
    member=Output.concat('serviceAccount:',gke_sa.email),
    project = proj,
    role="roles/compute.networkAdmin")
    
primary = gcp.container.Cluster("primary",
    location="us-central1",
    remove_default_node_pool=True,
    initial_node_count=1)
primary_spot_nodes = gcp.container.NodePool("worker-nodes-spot",
    location="us-central1",
    cluster=primary.name,
    name= "worker-nodes-spot",
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

ondemand_nodes = gcp.container.NodePool("worker-nodes-ondemand",
    location="us-central1",
    cluster=primary.name,
    node_count=0,
    name="worker-nodes-ondemand",
    node_config=gcp.container.NodePoolNodeConfigArgs(
        machine_type="e2-micro",
        service_account=gke_sa.email,
        oauth_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    ))

#create log metric to detect no scale up in Spot MIG
spot_mig_no_scale_up_metric = gcp.logging.Metric("SpotMigNoScaleUpMetric",
    filter=Output.concat('resource.type=k8s_cluster AND resource.labels.location= us-central1 AND resource.labels.cluster_name=',
    primary.name,
    ' AND severity>=DEFAULT AND jsonPayload.noDecisionStatus.noScaleUp.napFailureReason.messageId=no.scale.up.nap.disabled'),
    metric_descriptor=gcp.logging.MetricMetricDescriptorArgs(
        metric_kind="DELTA",
        value_type="INT64",
    ))

#create pupsub topic for cloudfunction trigger
pubsub = gcp.pubsub.Topic("SpotMigNoScaleUp")



#create logsink for publishing to Pubsub
log_sink = gcp.logging.ProjectSink("SpotMigNoScaleUpSink",
    destination=Output.concat('pubsub.googleapis.com/projects/',proj,'/topics/',pubsub.name),
    filter=Output.concat('resource.type=k8s_cluster AND resource.labels.location= us-central1 AND resource.labels.cluster_name='
    ,primary.name,
    ' AND severity>=DEFAULT AND jsonPayload.noDecisionStatus.noScaleUp.napFailureReason.messageId=no.scale.up.nap.disabled'),
    unique_writer_identity=True)

log_sink_perm = gcp.projects.IAMMember("log-sink-perm",
    member=log_sink.writer_identity,
    project = proj,
    role="roles/pubsub.publisher")


#cloud funtion to scale up the on-demand node group
bucket = gcp.storage.Bucket("scale-up-ondemand-np",location=location)

py_bucket_object = gcp.storage.BucketObject(
    "scale-up-zip",
    bucket=bucket.name,
    source=pulumi.asset.AssetArchive({
        ".": pulumi.asset.FileArchive("./functions/scale-up-ondemand-np")
    }))

py_function = gcp.cloudfunctions.Function(
    "scale-up-ondemand-np",
    source_archive_bucket=bucket.name,
    runtime="python37",
    source_archive_object=py_bucket_object.name,
    entry_point="handler",
    service_account_email=gke_sa.email,
    event_trigger= gcp.cloudfunctions.FunctionEventTriggerArgs(event_type="providers/cloud.pubsub/eventTypes/topic.publish",resource=pubsub.name),
    available_memory_mb=512,
)

py_invoker = gcp.cloudfunctions.FunctionIamMember(
    "py-invoker",
    project=py_function.project,
    region=py_function.region,
    cloud_function=py_function.name,
    role="roles/cloudfunctions.invoker",
    member="allUsers",
)

#cloud function to scale down on-demand periodically

py_bucket_object2 = gcp.storage.BucketObject(
    "scale-down-zip",
    bucket=bucket.name,
    source=pulumi.asset.AssetArchive({
        ".": pulumi.asset.FileArchive("./functions/scale-down-ondemand-np")
    }))

py_function2 = gcp.cloudfunctions.Function(
    "scale-down-ondemand-np",
    source_archive_bucket=bucket.name,
    runtime="python37",
    source_archive_object=py_bucket_object2.name,
    entry_point="handler",
    service_account_email=gke_sa.email,
    trigger_http = True,
    available_memory_mb=512,
)
request_body =  Output.all(f"{{'nodepool':'/projects/{proj}/zones/us-central1/clusters/{primary.name}/nodePools/{ondemand_nodes.name}}}").apply(lambda request_body:string_to_base64(request_body[0]))
job = gcp.cloudscheduler.Job("trigger-scale-down-ondemand-np",
  
    attempt_deadline="320s",
    description="trigger scale down on demand node pool",
    schedule="0 * * * *",
    time_zone="America/Denver",
    http_target=gcp.cloudscheduler.JobHttpTargetArgs(uri=py_function2.https_trigger_url, body=request_body, http_method='POST'))