from setuptools import setup, find_packages
readme = open('README.md').read()
setup(name='accounts',
      version='0.1',
      author='Marcos Bartolome',
      author_email='m@rcosbartolo.me',
      license='MIT',
      description='TDAF Accounts Openstack service daemons',
      long_description=readme,
      packages=find_packages(),
      # scripts to be copied to /usr/bin/
      scripts=['bin/accounts-api', 'bin/accounts-engine', 'accounts-manage'],
      # data_files to be copied to /etc
      data_files=[('/etc/accounts', [
                        'api-paste.ini,' 'accounts-api.conf', 'accounts.conf',
                        'accounts-engine.conf'
                    ]),
                    ('/etc/init.d', [
                        'init.d/accounts-engine',
                        'init.d/accounts-api',
                    ]),],
      )


