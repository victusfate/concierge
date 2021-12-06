#!/usr/bin/env sh
sleep 3
consul_addr=$(echo http://$CONSUL_HOST:8500)
aws_key=$(consul kv get -http-addr=$consul_addr 'aws/auth/concierge/key')
aws_secret=$(consul kv get -http-addr=$consul_addr 'aws/auth/concierge/secret')
aws_region=$(consul kv get -http-addr=$consul_addr 'aws/region')

mkdir /root/.aws
printf "[default]\naws_access_key_id = $aws_key\naws_secret_access_key = $aws_secret\n" > /root/.aws/credentials
chmod u+rw,og-rwx /root/.aws/credentials

# printf "[default]\nregion = $aws_region\n" > /root/.aws/config
# chmod u+rw,og-rwx /root/.aws/config

echo "consul_addr $consul_addr"
echo $(which python)
echo $(which pip)
echo $(which python3)
echo $(which pip3)
echo $(uname -s | tr A-Z a-z)
echo "$aws_region"

/usr/bin/python3 /var/www/concierge/bin/server.py