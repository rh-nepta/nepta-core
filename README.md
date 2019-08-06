Network Performance Test Automatization - CORE
===========================
* TBD


DEPENDENCIES
------------
For simple installation, all dependencies are specified in `Pipfile`. To 
install and run **nepta** use following shell commands:

```bash
git clone https://github.com/rh-nepta/nepta-core
cd nepta-core
pipenv install
python3 setup.py install
nepta --help
```
##### Required
* [xml-diff](https://pypi.org/project/xmldiff/)
* [jinja2](https://pypi.org/project/Jinja2/)
* [nepta-dataformat](https://github.com/rh-nepta/nepta-dataformat)

##### Optional
* [nepta-synchronization](https://github.com/rh-nepta/nepta-synchronization)



USAGE
-----
These command can be used to print configuration, setup server for test and run test.
```bash
# import and print configuration named "Default" of host "host_1.testlab.org"
nepta -i example_config . -p -c Default -e fqdn host_1.testlab.org

#import, setup and run tests according to configuration and store results in the end of test 
nepta -i example_config . -c Default -e fqdn host_1.testlab.org --setup --prepare --execute --store --store-logs
```
