Accounts
---------

To integrate Accounts services with RHEL & CENTOS startup sequence, follow this steps:

1- Create accounts OS user (the processes will run under this security account)
2- Copy init.d scripts to /etc/init.d
3- Set init scripts owner to root (chown root:root /etc/init/accounts*.conf)
4- Configure automatic startup
	chkconfig --add accounts-engine
	chkconfig --add accounts-api
	
