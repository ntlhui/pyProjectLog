from setuptools import setup, find_packages
import ProjectLog
setup(
    name='pyProjectLog',
    version=ProjectLog.__version__,
    description="Project Task Log",
    author='Nathan Hui',
    author_email='ntlhui@gmail.com',
    install_requires=[
        'appdirs',
        'tkcalendar',
        'schema',
        'pyYaml'
    ],
    packages=find_packages(),
    entry_points={
        'console_scripts':[
            'ProjectLog=ProjectLog.projectLog:main'
        ]
    }
)