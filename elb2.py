#!/usr/bin/python
import urllib2  
import time
import boto.ec2.elb
from boto.ec2.elb import HealthCheck
import boto.ec2.autoscale
from boto.ec2.autoscale import LaunchConfiguration
from boto.ec2.autoscale import AutoScalingGroup
from boto.ec2.autoscale import ScalingPolicy
import boto.ec2.cloudwatch
from boto.ec2.cloudwatch import MetricAlarm
import boto.ec2

#Create an ELB that:
#Redirects HTTP:80 requests from the load balancer to HTTP:80 on the instance
#Record the DNS Name of the created ELB
#Set up the page /heartbeat?username=<yourandrewid> as the health check page
#If you remember from last week, a data center instance needs to be activated by passing it your username. This step ensures that the ELB passes your username to your data center instances.

elb=boto.ec2.elb.connect_to_region('us-east-1')
hc=HealthCheck(interval=5,healthy_threshold=2,timeout=2,unhealthy_threshold=2,target='HTTP:80/heartbeat?username=jianj')
zones=['us-east-1a']
ports=[(80,80,'http')]
lb=elb.create_load_balancer('jianLb',zones,ports)
lb.configure_health_check(hc)
lbdns=lb.dns_name
print 'load banlancer dns name:%s'%(lbdns)

#Create a Launch Configuration for the instances that will become part of the auto scaling group, with the following parameters:
#AMI ID: ami-ec14ba84
#Instance Type: m3.medium
#Detailed Monitoring: enabled
autoscale=boto.ec2.autoscale.connect_to_region('us-east-1') #the client
#lc
lc=LaunchConfiguration(name='jianLaunchConfig',image_id='ami-3c8f3a54',key_name='jj',security_groups=['http'],instance_type='m3.medium',instance_monitoring=True)
autoscale.create_launch_configuration(lc)
print 'launch cofig created'
#ag
ag=AutoScalingGroup(group_name='jianGroup',load_balancers=['jianLb'],availability_zones=['us-east-1a'],launch_config=lc,min_size=2,max_size=4,connection=autoscale)
autoscale.create_auto_scaling_group(ag)
ag.put_notification_configuration(topic="arn:aws:sns:us-east-1:683895670525:launch",notification_types=['autoscaling:EC2_INSTANCE_LAUNCH', 'autoscaling:EC2_INSTANCE_LAUNCH_ERROR'])
ag.put_notification_configuration(topic="arn:aws:sns:us-east-1:683895670525:terminate",notification_types=['autoscaling:EC2_INSTANCE_TERMINATE','autoscaling:EC2_INSTANCE_TERMINATE_ERROR'])
print 'aotuscaling group createc'
#scaling policy
scale_up_policy=ScalingPolicy(name='jianScaleUp',adjustment_type='ChangeInCapacity',as_name='jianGroup',scaling_adjustment=2,cooldown=60)
scale_down_policy=ScalingPolicy(name='jianScaleDown',adjustment_type='ChangeInCapacity',as_name='jianGroup',scaling_adjustment=-2,cooldown=120)
#submit to aws
autoscale.create_scaling_policy(scale_up_policy)
autoscale.create_scaling_policy(scale_down_policy)
#request back again
scale_up_policy=autoscale.get_all_policies(as_group='jianGroup',policy_names=['jianScaleUp'])[0]
scale_down_policy=autoscale.get_all_policies(as_group='jianGroup',policy_names=['jianScaleDown'])[0]
print 'scaling policy created'

##cloud watch
cloudwatch=boto.ec2.cloudwatch.connect_to_region('us-east-1')
alarm_dimensions={"AutoScalingGroupName":'jianGroup'}
#scale up
scale_up_alarm=MetricAlarm(name='scale_up_on_cpu',namespace='AWS/EC2',metric='CPUUtilization',statistic='Average',comparison='>',threshold='80',period='60',evaluation_periods=1,alarm_actions=[scale_up_policy.policy_arn],dimensions=alarm_dimensions)
cloudwatch.create_alarm(scale_up_alarm)
#scale down
scale_down_alarm = MetricAlarm(name='scale_down_on_cpu', namespace='AWS/EC2',metric='CPUUtilization', statistic='Average',comparison='<', threshold='60',period='60', evaluation_periods=1,alarm_actions=[scale_down_policy.policy_arn],dimensions=alarm_dimensions)
cloudwatch.create_alarm(scale_down_alarm)
print 'both clock watch created'

#load generator
ec2=boto.ec2.connect_to_region("us-east-1")
reservation=ec2.run_instances('ami-7aba0c12',key_name='jj',instance_type='m3.medium',security_groups=['http'])
time.sleep(60)
instance=reservation.instances[0]
id=instance.id

#loadDns=instance.public_dns_name
#get load dns
groupw=autoscale.get_all_groups(names=['jianGroup'])[0]
instances=ec2.get_only_instances(instance_ids=[id])
loadDns=instances[0].public_dns_name
print 'load generator dns is :%s'%(loadDns)

time.sleep(10)
#authenticate
response = urllib2.urlopen('http://'+loadDns+'/username?username=jianj')
print 'load generator authenticated'


#warm up
response=urllib2.urlopen('http://'+loadDns+'/warmup?dns='+lbdns+'&testId=jian')
print 'warm up started'
time.sleep(310)
print 'warmed up first time'
response=urllib2.urlopen('http://'+loadDns+'/warmup?dns='+lbdns+'&testId=jian')
print 'second warm up started'
time.sleep(310)
print 'warmed up second time'
response=urllib2.urlopen('http://'+loadDns+'/warmup?dns='+lbdns+'&testId=jian')
print 'third warm up started'
time.sleep(310)
print 'warmed up third time'

#start test
response=urllib2.urlopen('http://'+loadDns+'/begin-phase-3?dns='+lbdns+'&testId=jian')
print 'test started'

#shut down instances
#ag.shutdown_instances()
#time.sleep(180)
#ag.delete()
#lc.delete()
