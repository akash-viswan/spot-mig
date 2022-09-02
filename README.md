# spot-mig

We aim to make spot instances more suitable for time-sensitive workloads by offloading tasks to on-demand servers in the event of 
the unavailability of spot instances. Thus taking advantage of the lower cost Spot provides.

![image](https://user-images.githubusercontent.com/92756509/188229644-ffad3105-299a-4efa-a982-690b62d47a32.png)


Solution built using two similar GKE NodePools for managing workloads. One node pool uses spot instances and 
the second one uses regular on-demand instances.
Spot node pool auto-scale to deploy new workloads on spot node group first.
On-demand node-pool are scaled up only if the spot node-pool didn't scale and pods are pending.
Detection of spot node pool unable to scale is achieved by a log filter that looks for the NoScaleUp event in the GKE cluster logs.
This log event triggeres a cloud function via cloud pub/sub to scale up the on-demand node group.
Scale up on the on-demand node group allows GKE to deploy a workload to on-demand node group.
Thus preventing an indefinite wait due to unavailability of spot instances.

A cloud scheduler-initiated cloud function periodically scales down on-demand node group allowing workloads to shift to spot node groups.
It prevents workloads from running on on-demand node groups for a longer period while spot instances are available.
