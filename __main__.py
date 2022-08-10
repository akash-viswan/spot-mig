#create GKE Cluster and nodepools
import pulumi_gcp as gcp
from pulumi import Output
import pulumi

config = pulumi.Config('gcp')
proj = config.get('project')
location = config.get('region')

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
    event_trigger= gcp.cloudfunctions.FunctionEventTriggerArgs(event_type="providers/cloud.pubsub/eventTypes/topic.publish",resource=pubsub.name),
    available_memory_mb=128,
)

py_invoker = gcp.cloudfunctions.FunctionIamMember(
    "py-invoker",
    project=py_function.project,
    region=py_function.region,
    cloud_function=py_function.name,
    role="roles/cloudfunctions.invoker",
    member="allUsers",
)