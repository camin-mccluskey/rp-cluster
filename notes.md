### Copying Ghostty terminfo

Run on each node: `infocmp -x xterm-ghostty | ssh YOUR-SERVER -- tic -x -` 

### Localstack

Install Helm and deploy localstack Helm chart to cluster:
https://docs.localstack.cloud/aws/getting-started/installation/#deploy-localstack-using-helm

```
helm repo add localstack-repo https://helm.localstack.cloud
helm upgrade --install localstack localstack-repo/localstack
```
 
Then follow instruction to get application URL

```
export NODE_PORT=$(kubectl get --namespace "default" -o jsonpath="{.spec.ports[0].nodePort}" services localstack)
export NODE_IP=$(kubectl get nodes --namespace "default" -o jsonpath="{.items[0].status.addresses[0].address}")
echo http://$NODE_IP:$NODE_PORT
```

Install and confgiure AWS cli + localstack. Create a profile for localstack in ~/.aws/config and ~/.aws/credentials (dummy creds)

config:
```
[profile localstack]
region = us-east-1
output = json
endpoint_url = http://192.168.1.100:31566
```

Check localstack is running on port on cluster:
```
aws s3 ls --profile localstack
```

(if desired) Configure localstack AWS CLI (awslocal) to use cluster endpoint:

In ~/.localstack/default.env
```
AWS_ENDPOINT_URL=http://192.168.1.100:31566
GATEWAY_LISTEN=0.0.0.0:4566
```
