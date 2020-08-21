import os
import yaml

# Load the config and get the headers setup
config = os.environ.get('GITISSUEBOT_CONFIG', None)

if config:
    with open(config, 'r') as stream:
        config = yaml.safe_load(stream)