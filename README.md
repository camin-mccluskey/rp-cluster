# Raspberry Pi Cluster

First step is to get your PIs setup and connected to the network with a fixed IP address. You can wire the devices directly to your network using LAN cables or use a wireless router. A wired connection is recommended for stability and performance. However I've opted for a wireless setup so I can look at my beautiful cluster on my desk. 

You'll need to install an operating system on each of the PIs. I've opted for the Raspian Lite OS. I'd recommend using Raspberry Pi imager to flash each of the SD cards. As you do so, you'll need to set up some important settings:
- A host name for each of the PIs. This must be unique and will be used throughout to identify each node in the cluster. I've used `rp-master`, `rp-node-1` and `rp-node-2` for the master and agent nodes.
- Network access. If you're using the Lite version of the OS, you should configure network settings now to ensure you can access the PIs from your development machine later.
- A username and password must be set
- Finally, you'll need to enable SSH access to the PIs. This will allow you to connect to the PIs over the network.

Once you've flashed the images, installed the SD cards, and powered up the PI's, validate you can connect to each node via SSH. Run `arp -a` to view a list of devices on your network. You should see the PIs listed with their IP addresses. 

You can now connect to each PI by running `ssh <username>@<ip-address>`.

When you ran `arp -a` you will have also seen the MAC addresses of each PI. It's worth taking some time to reserve a static IP address for each PI in your router DCHP settings. This will mean we have a fixed IP address for each node we can continue to reference as we build out the cluster. You can configure DCHP settings in your router's web interface. You can typically Google how to do this for your brand of router. It's useful to reserve memorable, adjacent IP addresses for each node.

I find at this point it's helpful to configure `HostName`s in your `.ssh/config` file. This will allow you to reference the PIs by their hostnames rather than their IP addresses. The rest of the guide will assume you've completed this step.

Using k3s and k3sup. <- ==Add full tutorial on building up the PIs and getting setup with k3sup etc later==

Installing k3sup
brew install k3sup ( or the git version - see docs)

Before we get to the meat of setting up the cluster, we'll need to adjust some settings on each of the Pis. To make life a bit easier, from this point on we'll use Ansible to configure each of the Pis in a scalable way. This avoids the need to ssh into each manually and run commands. I'll let you know what each Ansible playbook is doing as we go, and you can always peek inside each to check. 

First install Ansible on your development machine. 

```
brew install ansible
```

Now you'll need to configure an `inventory.ini` file. This a simple file that lists the PIs in the cluster, along with some details about each node. Critically, this will configure the IP address of each node in the cluster.

Example inventory.ini file:
```
[pis]
rp-master ansible_host=rp-master ansible_user=pi k3s_service_name=k3s
rp-node-1 ansible_host=rp-node-1 ansible_user=pi k3s_service_name=k3s-agent
rp-node-2 ansible_host=rp-node-2 ansible_user=pi k3s_service_name=k3s-agent
```

Now we can run the first Ansible playbook to enable cgroup_memory. This is required for k3s to run on Raspbian and Ubuntu. If you're using a different OS, you can proceed to the next step.

```
ansible-playbook -i inventory.ini cgroup_memory.yaml
```

This playbook will reboot the PIs to apply the changes.

Now we can begin to install k3s on the cluster.

Setup the master node as the k3s server
k3sup install --ip <master-node-ip> --user <user> --ssh-key <path-to-ssh-key>
Note your ssh key may vary - it's going to be whatever you copied across to your pi(s) when you flashed the image.
By default k3sup will use id_rsa

Now join some agents to your K3s server with
k3sup join --ip <agent-node-1-ip> --server-ip <master-node-ip> --user <user> --ssh-key <path-to-ssh-key>
k3sup join --ip <agent-node-2-ip> --server-ip <master-node-ip> --user <user> --ssh-key <path-to-ssh-key>

From here on you should always make sure you're connected to the cluster: `k3sup get-config --host <master-node-ip> --user <user>`. This will output your
cluster KUBECONFIG which you should set as an envar before running kubectl commands.

## Deploying your first application

Before we can deploy our first application, we'll set up a local docker registry. This will allow us to push images to the cluster, and have cluster nodes pull images from the registry locally, rather than pulling from a remote registry. 

We'll first ready the cluster to allow insecure registries. This is required for cluster nodes to pull images from the local registry. Again, we have an Ansible playbook for this.

```
ansible-playbook -i inventory.ini registry.yaml
```
This playbook will add a registry mirror to the cluster nodes and will restart the k3s service on each node.

We'll also need to allow our local machine to operate using a local registry:
On mac/windows:
 • Go to Docker Desktop → Settings → Docker Engine.
 • Add `"insecure-registries": ["192.168.1.100:30500"]` to the JSON. (also rp-mster).
 • Click “Apply & Restart”.
On linux:
add { "insecure-registries": ["192.168.1.100:30500"] } to /etc/docker/daemon.json

Now we can deploy our registry by running the following commands (ensuring you have set your KUBECONFIG environment variable first):

```
kubectl apply -f registry-deployment.yaml
kubectl apply -f registry-service.yaml
```
You can now check the registry is running by running `kubectl get pods`. You should see 1 pod running with the name `local-registry-*`.

Finally, we're ready to build and push our first image to the cluster. We'll use a simple Flask application to test the cluster.

First, build and tag the image:
`docker build -t 192.168.1.100:30500/rpi-flask-test:latest ./simple-webserver`
_it's worth noting what exactly is happening with this command. We're building the docker image from the Dockerfile in the `simple-webserver` directory. We're then tagging the image with the registry name and the port we're using for the registry (this is our local registry). We're also using the `latest` tag to indicate the latest version of the image._

Now push the tagged image to the cluster:

`docker push 192.168.1.100:30500/rpi-flask-test:latest`
_Note: it's helpful to see if your image has been pushed to run `curl http://192.168.1.100:30500/v2/_catalog`. You should see the image listed in the repositories key of the response._


Finally, with our image pushed to the registry, we can deploy our application by running:

```
kubectl apply -f simple-webserver/deployment.yaml
kubectl apply -f simple-webserver/service.yaml
```

This will start a deployment. Again you can check the deployment has completed successfully by running `kubectl get pods`. You should see 3 pods running with the name `rpi-flask-test-*`.

From here there is much more to explore in terms of networking, loadbalancing etc. But this will get you started with
a simple deployment of a 3 pod cluster and service to expose these pods to the local network. You can now access the application by visiting `http://<any-node-host-name>:30501/` in your browser. You should see a simple "Hello, World!" message.

## Going Further: Deploying a stateful application

Let's say we want to deploy a stateful application, such that the services running on each pod are sharing data. To illustrate this, we'll deploy a simple web application that increments a counter on each request. 

## NFS: Boot Drive 

Each of the nodes in your cluster will have an SD card to boot from. If you're running services inside the cluster, it's  
likely you'll want larger storage for things like logs or data. It's possible to boot from a USB drive with newer PIs but 
for the purposes of this demo we'll simply attach a USB SSD to act as storage for the cluster.

This requires a bit of setup so Ansible is recommended here: `ansible-playbook -i inventory.yaml nfs.yaml`
You may need to tweak the nfs.yaml file to use the correct `ssd_device`. You can find out the main partition of your
SSD by running `lsblk` on the storage attached pi - you're looking for the largest partition on the disk. You may want 
to follow a guide to reformat (accepting you'll lose any data on the SSD).

You'll need to make sure that the partition is of type `ext4`. You can check the filesystem type with `sudo blkid /dev/sda1`
and if it's not, format it with `sudo mfs.ext4 /dev/sda1`. (or sda2, 3 etc if that's your main partition).

You can now expose NFS to Kubernetes Pods - `kubectl apply -f k3s/nfs-pv.yaml`

We can now deploy a stateful service to test the NFS (would a stateful service not have worked before?? No by default state
is not shared across pods running in different nodes).

Now we can deploy our stateful application by running:

```
docker build -t rp-master:30500/rpi-stateful:latest ./stateful-webserver
docker push rp-master:30500/rpi-stateful:latest
kubectl apply -f stateful-webserver/deployment.yaml
kubectl apply -f stateful-webserver/service.yaml
```

## Final Goodies

### Tailing logs from your pods

Useful to see what's actually going in
`kubectl get pods -A` to see a full list of the pods
`kubectl logs -f <pod-name> -n <namespace>`

Or to see log for all pods in a deployment
`kubectl get pods -n <namespace> -l app=<app-label> -o name | xargs -I {} kubectl logs -f {} -n <namespace>`

### Updating your deployments

I assume you're going to want to change something about the current code

kubectl set image deployment/rpi-stateful app=rp-master:30500/rpi-stateful:latest