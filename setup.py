from setuptools import setup, find_packages
readme = open('README.md').read()
setup(name='accounts',
      version='0.1',
      author='Marcos Bartolome',
      author_email='m@rcosbartolo.me',
      license='MIT',
      description='TDAF Accounts Openstack service daemons',
      long_description=readme,
      packages=find_packages())

