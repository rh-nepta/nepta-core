Network Performance Test Automatization - CORE
===========================

## Introduction
Nepta-core is designed to automate network performance testing, offering
a comprehensive solution for assessing and enhancing network efficiency. 
This project simplifies complex network testing tasks, ensuring accurate
and reliable performance evaluations.


DEPENDENCIES
------------
For an easy setup, the project lists all necessary dependencies within the
`hatch environment` file. Follow these shell commands to clone, set up the 
environment, and start using `nepta`:

```bash
git clone https://github.com/rh-nepta/nepta-core
cd nepta-core
hatch shell
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
