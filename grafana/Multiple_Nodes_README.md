In order to not repeat the same information coming from multiple nodes, we have a filter added to some metrics like so:

chia_network_space{job="NODE1"}

where NODE1 is the job_name attribute configured in prometheus.yml. You can put in the name of any node, what matters is that we only get one value instead of 2 or 3.

Open the dashboard file you want to use "dashboardv2_dual_node_xxxxx.json" and search/replace NODE1 by the name of one of your jobs.