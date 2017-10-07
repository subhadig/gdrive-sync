from setuptools import setup, find_packages

setup(
        name='gdrive-sync',
        version='0.1.dev',
        packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
        author='Subhadip Ghosh',
        author_email='subhadipghosh11@gmail.com',
        description='A Google drive client',
        long_description=open('README.txt').read(),
        classifiers=[
        'Development Status :: Beta',
        'Programming Language :: Python :: 3.5',
        'Topic :: Google drive client',
        ],
        install_requires=['google-api-python-client',
                          'watchdog',
                          'pydblite',
                          'python-magic'],
        entry_points={
            'console_scripts': [
                #'run-ios-push-server=batch.servers.ios_push_client_server:run_server'
            ]
        },
        include_package_data=True,
        test_suite='tests'
)
