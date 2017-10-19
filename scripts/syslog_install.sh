#!/bin/bash -v

# First make cloud-init output log readable by root only to protect sensitive parameter values
chmod 600 /var/log/cloud-init-output.log

# get latest aws-cfn-bootstrap package
yum update -y aws-cfn-bootstrap

# Environment variables
export SPLUNK_USER=splunk
export SPLUNK_BIN=/opt/splunkforwarder/bin/splunk
export SPLUNK_HOME=/opt/splunkforwarder
export PATH=$PATH:/opt/aws/bin
export APPDIR=/opt/splunkforwarder/etc/apps/pan-splunk-syslog/default
export APPDIRROOT=/opt/splunkforwarder/etc/apps/pan-splunk-syslog/

# Stop Splunk, install the splunk forwarder, and reset password
/opt/splunk/bin/splunk stop

#install splunk universal forwarder
rpm -i /tmp/splunk-uf.rpm 

sed -i 's/force-change-pass true//' /etc/init.d/splunk
sudo -u $SPLUNK_USER $SPLUNK_BIN edit user admin -password {{SPLUNK_ADMIN_PASSWORD}} -role admin -auth admin:changeme

#chown $SPLUNK_USER:$SPLUNK_USER $SPLUNK_HOME/etc/system/local/server.conf
# install syslog-ng and configure init

yum -y install --enablerepo=epel syslog-ng syslog-ng-libdbi
chkconfig --add syslog-ng
chkconfig syslog-ng on

# install syslog-ng config
mkdir -p /var/log/syslog-ng
service syslog-ng start

# run templating on the splunk configs
tar xvf /tmp/splunk-pan-syslog-app.tar.gz -C /opt/splunkforwarder/etc/apps && rm -f /tmp/splunk-pan-syslog-app.tar.gz
cat $APPDIR/outputs.conf | /tmp/mo > $APPDIR/outputs.conf.new
mv $APPDIR/outputs.conf.new $APPDIR/outputs.conf

chown -R $SPLUNK_USER:$SPLUNK_USER $APPDIRROOT

#start splunk
$SPLUNK_BIN start --accept-license


cfn-signal -s true --stack $AWSSTACKNAME --resource SplunkSyslogNodesASG --region $AWSREGION

# Disable splunk user login
usermod --expiredate 1 splunk

