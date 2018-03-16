from setuptools import setup, find_packages

setup(
    name="hellomama-registration",
    version="0.1.2",
    url='http://github.com/praekelt/hellomama-registration',
    license='BSD',
    author='Praekelt Foundation',
    author_email='dev@praekeltfoundation.org',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django==1.9.1',
        'djangorestframework==3.3.2',
        'dj-database-url==0.3.0',
        'psycopg2==2.7.3.1',
        'raven==5.10.0',
        'django-filter==0.12.0',
        'whitenoise==2.0.6',
        'celery==3.1.19',
        'django-celery==3.1.17',
        'redis==2.10.5',
        'openpyxl==2.4.0',
        'pytz==2015.7',
        'python-dateutil==2.5.3',
        'six==1.10.0',
        'django-rest-hooks==1.3.1',
        'django-filter==0.12.0',
        'seed-services-client>=0.33.0',
        'drfdocs==0.0.11',
        'pika==0.10.0',
        'sftpclone==1.2',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
