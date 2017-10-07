#!/bin/bash -v

# First make cloud-init output log readable by root only to protect sensitive parameter values
chmod 600 /var/log/cloud-init-output.log

# get latest aws-cfn-bootstrap package
yum update -y aws-cfn-bootstrap

# Environment variables
export SPLUNK_USER=splunk
export SPLUNK_BIN=/opt/splunk/bin/splunk
export SPLUNK_HOME=/opt/splunk
export PATH=$PATH:/opt/aws/bin
export APPDIR=/opt/splunk/etc/apps/pan-splunk-syslog/default
export APPDIRROOT=/opt/splunk/etc/apps/pan-splunk-syslog/

# Stop Splunk and reset password
service splunk stop
touch $SPLUNK_HOME/etc/.ui_login
mv $SPLUNK_HOME/etc/passwd $SPLUNK_HOME/etc/passwd.bak
sed -i 's/force-change-pass true//' /etc/init.d/splunk
sudo -u $SPLUNK_USER $SPLUNK_BIN edit user admin -password {{SPLUNK_ADMIN_PASSWORD}} -role admin -auth admin:changeme

chown $SPLUNK_USER:$SPLUNK_USER $SPLUNK_HOME/etc/system/local/server.conf


# remove original rsyslog, install syslog-ng, and configure init
rpm -e --nodeps rsyslog
yum -y install --enablerepo=epel syslog-ng syslog-ng-libdbi
chkconfig --add syslog-ng
chkconfig syslog-ng on

# install syslog-ng config
mkdir -p /var/log/syslog-ng
service syslog-ng start

# run templating on the splunk configs
tar xvf /tmp/splunk-pan-syslog-app.tar.gz -C /opt/splunk/etc/apps && rm -f /tmp/splunk-pan-syslog-app.tar.gz
cat $APPDIR/outputs.conf | /tmp/mo > $APPDIR/outputs.conf.new
mv $APPDIR/outputs.conf.new $APPDIR/outputs.conf

chown -R $SPLUNK_USER:$SPLUNK_USER $APPDIRROOT

service splunk start
cfn-signal -s true --stack $AWSSTACKNAME --resource SplunkSyslogNodesASG --region $AWSREGION

# Disable splunk user login
usermod --expiredate 1 splunk

