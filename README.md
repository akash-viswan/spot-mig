# spot-mig

We aim to make spot instances more suitable for time sensitive workload by offloading task to on-demand servers in the event of 
unavailability of spot instances. Thus taking advantage of lower cost Spot provides.

![image](https://user-images.githubusercontent.com/92756509/188229644-ffad3105-299a-4efa-a982-690b62d47a32.png)


Solution is built using two similar GKE NodePools for managing workloads. One node pool uses spot instances and 
the second one uses regular on-demand instances.
Spot node pool is configured to auto-scale this is ensure new workloads are tried to deploy on spot node group first.
On-demand node pool are scaled up only if spot node pool was unable to scale and there are pods pending.
Detection of spot node pool unable to scale is achived by a log filter that looks for NoScaleUp event in the gke cluster logs.
The log event triggers and cloud function via cloud pub/sub that will triggere the scale up on the on-demand node group.
This scale up on the on-demand node group allows GKE to deploy workload to ondemand node group.
Thus prevending an indefinite wait for spot instance.

A cloud scheduler initated cloud function periodicaly scale down on-demand node group allowing workloads to be shifted to spot node groups.
This prevents workloads running on on-demand for a longer period while there are spot instances are available.


