import bsb_yaml
import bsb
import importlib.metadata

print(bsb)
print(bsb_yaml)

installed_packages = importlib.metadata.distributions()
for package in installed_packages:
    print(package.metadata['Name'])